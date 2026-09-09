from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.clients import client_detail, client_row, clients_queryset
from chatballs.conversations.contacts_merge import merge_contacts, revert_merge
from chatballs.conversations.models import Contact
from chatballs.conversations.stats import sales_overview_stats
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole


class ConversationStatsView(ConversationViewBase):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(sales_overview_stats(request.tenant_context, period))


class ClientsView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        """Страница списка контактов: фильтры, поиск и порядок отрабатывает база."""
        page = paginate(
            clients_queryset(self._org(request).id, request.query_params),
            request.query_params,
        )
        return Response(page_payload(page, client_row))


class ClientDetailView(ConversationViewBase):
    required_capabilities = {"GET": "customers.view", "PATCH": "customers.manage"}
    # Те же поля и пределы, что у карточки контакта в чате (ConversationContactView).
    LIMITS = {"name": 255, "description": 2000, "phone": 32, "company": 160, "city": 120}

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            return Response({"client": client_detail(self._org(request).id, contact_id)})
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)

    def patch(self, request: Request, contact_id: int) -> Response:
        organization = self._org(request)
        try:
            contact = Contact.objects.get(id=contact_id, organization=organization)
        except Contact.DoesNotExist:
            return Response({"detail": "Клиент не найден"}, status=404)
        changed: list[str] = []
        for field, limit in self.LIMITS.items():
            if field not in request.data:
                continue
            value = str(request.data.get(field) or "").strip()
            if len(value) > limit:
                return Response({"detail": f"Поле {field}: не длиннее {limit} символов"}, status=400)
            if field == "name" and not value:
                return Response({"detail": "Имя контакта не может быть пустым"}, status=400)
            setattr(contact, field, value)
            changed.append(field)
        if changed:
            contact.save(update_fields=changed)
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
            return Response({"detail": "Объединять контакты может только владелец"}, status=403)
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
