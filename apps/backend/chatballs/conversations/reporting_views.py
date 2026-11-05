from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations import contact_services
from chatballs.conversations.models import Contact
from chatballs.conversations.stats import sales_overview_stats
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


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
        try:
            contact = contact_services.avatar(request.tenant_context, contact_id)
        except Contact.DoesNotExist:
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
        return Response(contact_services.contacts(request.tenant_context, request.query_params))


class ClientDetailView(ConversationViewBase):
    required_capabilities = {"GET": "customers.view", "PATCH": "customers.manage"}

    def get(self, request: Request, contact_id: int) -> Response:
        try:
            return Response({"client": contact_services.card(request.tenant_context, contact_id)["client"]})
        except Contact.DoesNotExist:
            return Response({"detail": t("sales.client_not_found")}, status=404)

    def patch(self, request: Request, contact_id: int) -> Response:
        try:
            return Response(contact_services.change_card(request.tenant_context, contact_id, request.data, request=request))
        except Contact.DoesNotExist:
            return Response({"detail": t("sales.client_not_found")}, status=404)



class ClientMergeView(ConversationViewBase):
    """Объединение контактов и обратное разъединение (ADR-CHATBALLS-0006).

    Доступно только владельцу, требует причины и полностью аудируется;
    предложение объединения на карточке видят и администраторы.
    """

    required_capabilities = {"POST": "customers.manage", "DELETE": "customers.manage"}

    def post(self, request: Request, contact_id: int) -> Response:
        try:
            return Response(contact_services.merge(request.tenant_context, contact_id,
                int(request.data.get("sourceId") or 0), str(request.data.get("reason", "")), request=request))
        except ValidationError as error:
            return Response({"detail": "; ".join(error.messages)}, status=400)

    def delete(self, request: Request, contact_id: int) -> Response:
        try:
            return Response(contact_services.unmerge(request.tenant_context, contact_id,
                int(request.data.get("mergeId") or 0), str(request.data.get("reason", "")), request=request))
        except ValidationError as error:
            return Response({"detail": "; ".join(error.messages)}, status=400)
