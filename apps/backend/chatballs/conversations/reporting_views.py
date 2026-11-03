from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.clients import client_detail, client_row, clients_queryset
from chatballs.conversations.contact_card import save_card_fields
from chatballs.conversations.contacts_merge import merge_contacts, revert_merge
from chatballs.conversations.models import Contact
from chatballs.conversations.selectors import visible_conversations_for
from chatballs.conversations.stats import sales_overview_stats
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole


class ConversationStatsView(ConversationViewBase):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(sales_overview_stats(request.tenant_context, period))


class ContactAvatarView(ConversationViewBase):
    """Фото контакта, скачанное у провайдера.

    Отдаётся со своего адреса: страница рабочего места живёт под CSP
    `img-src 'self'`, и ссылка на CDN мессенджера до экрана не доезжает.
    Видно тому же, кто видит диалоги, — фото клиента и есть часть карточки.
    """

    def get(self, request: Request, contact_id: int):
        contact = Contact.objects.filter(
            organization=self._org(request), id=contact_id
        ).first()
        if contact is None or not contact.avatar or not visible_conversations_for(request.tenant_context).filter(contact_id=contact_id).exists():
            return Response({"detail": t("sales.client_not_found")}, status=404)
        response = FileResponse(
            contact.avatar.open("rb"),
            content_type=contact.avatar_content_type or "application/octet-stream",
            filename="avatar",
        )
        response["Cache-Control"] = "private, max-age=86400"
        return response


class ClientsView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        """Страница списка контактов: фильтры, поиск и порядок отрабатывает база."""
        page = paginate(
            clients_queryset(self._org(request).id, request.query_params, context=request.tenant_context),
            request.query_params,
        )
        return Response(page_payload(page, client_row))


class ClientDetailView(ConversationViewBase):
    required_capabilities = {"GET": "customers.view", "PATCH": "customers.manage"}

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            return Response({"client": client_detail(self._org(request).id, contact_id, context=request.tenant_context)})
        except Contact.DoesNotExist:
            return Response({"detail": t("sales.client_not_found")}, status=404)

    def patch(self, request: Request, contact_id: int) -> Response:
        organization = self._org(request)
        try:
            contact = Contact.objects.get(id=contact_id, organization=organization)
        except Contact.DoesNotExist:
            return Response({"detail": t("sales.client_not_found")}, status=404)
        # Те же поля и пределы, что у карточки контакта в чате (ConversationContactView).
        changed, error = save_card_fields(contact, request.data)
        if error:
            return Response({"detail": error}, status=400)
        if changed:
            record_audit_event(
                action="conversation.contact_updated",
                actor=request.user,
                organization=organization,
                object_type="Contact",
                object_id=str(contact.id),
                payload={"fields": changed},
                request=request,
            )
        return Response({"client": client_detail(organization.id, contact_id)})


class ClientMergeView(ConversationViewBase):
    """Объединение контактов и обратное разъединение (ADR-CHATBALLS-0006).

    Доступно только владельцу, требует причины и полностью аудируется;
    предложение объединения на карточке видят и администраторы.
    """

    required_capabilities = {"POST": "customers.manage", "DELETE": "customers.manage"}

    def _owner_only(self, request: Request) -> Response | None:
        membership = request.tenant_context.membership
        if membership is None or membership.role != EmployeeRole.OWNER:
            return Response({"detail": t("sales.merge_owner_only")}, status=403)
        return None

    def post(self, request: Request, contact_id: int) -> Response:
        denied = self._owner_only(request)
        if denied is not None:
            return denied
        organization = self._org(request)
        try:
            merge_contacts(
                organization=organization,
                target_id=contact_id,
                source_id=int(request.data.get("sourceId") or 0),
                reason=str(request.data.get("reason", "")),
                actor=request.user,
                request=request,
            )
        except ValidationError as error:
            return Response({"detail": "; ".join(error.messages)}, status=400)
        return Response({"client": client_detail(organization.id, contact_id)})

    def delete(self, request: Request, contact_id: int) -> Response:
        denied = self._owner_only(request)
        if denied is not None:
            return denied
        organization = self._org(request)
        try:
            revert_merge(
                organization=organization,
                merge_id=int(request.data.get("mergeId") or 0),
                reason=str(request.data.get("reason", "")),
                actor=request.user,
                request=request,
            )
        except ValidationError as error:
            return Response({"detail": "; ".join(error.messages)}, status=400)
        return Response({"client": client_detail(organization.id, contact_id)})
