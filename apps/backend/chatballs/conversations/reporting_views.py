from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.clients import client_detail, clients_overview
from chatballs.conversations.models import Contact
from chatballs.conversations.stats import sales_overview_stats
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.identity.audit import record_audit_event


class ConversationStatsView(ConversationViewBase):
    def get(self, request: Request) -> Response:
        period = request.query_params.get("period", "today")
        if period not in ("today", "d7", "d30"):
            period = "today"
        return Response(sales_overview_stats(request.tenant_context, period))


class ClientsView(ConversationViewBase):
    required_capability = "customers.view"

    def get(self, request: Request) -> Response:
        return Response({"items": clients_overview(self._org(request).id)})


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
