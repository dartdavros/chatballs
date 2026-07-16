from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability, HasEntitlement
from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.policy import accessible_department_ids, require_capability
from hub_platform.products.models import Product
from hub_platform.sales.analytics import sales_analytics
from hub_platform.sales.models import Sale, SaleEventType
from hub_platform.sales.selectors import (
    apply_sale_filters,
    sale_for_context,
    sales_for_context,
)
from hub_platform.sales.serializers import sale_payload
from hub_platform.sales.services import (
    SalesApiError,
    create_manual_sale,
    issue_attribution_token,
    record_manual_action,
)


def _api_error(error: SalesApiError) -> Response:
    return Response({"detail": error.message, "error": error.error_code}, status=error.status_code)


class _Base(APIView):
    def _org(self, request: Request):
        return request.tenant_context.organization


class SaleListCreateView(_Base):
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "sales_department"
    required_capabilities = {"GET": "sales.view", "POST": "sales.operate"}

    def get(self, request: Request) -> Response:
        qs = apply_sale_filters(sales_for_context(request.tenant_context), request.query_params)
        department_ids = accessible_department_ids(request.tenant_context.membership, "sales.view")
        if department_ids is not None:
            qs = qs.filter(conversation__channel__department_id__in=department_ids)
        return Response({"items": [sale_payload(sale) for sale in qs]})

    def post(self, request: Request) -> Response:
        org = self._org(request)
        data = request.data

        try:
            product = Product.objects.get(organization=org, code=str(data.get("productCode", "")))
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=400)

        contact = None
        conversation = None
        if data.get("conversationId"):
            conversation = Conversation.objects.filter(id=data.get("conversationId"), organization=org).first()
            if conversation is None:
                return Response({"detail": "Conversation not found"}, status=400)
            if not require_capability(request.tenant_context.membership, "sales.operate", conversation):
                return Response({"detail": "Conversation not found"}, status=404)
        if data.get("contactId"):
            contact = Contact.objects.filter(id=data.get("contactId"), organization=org).first()
            if contact is None:
                return Response({"detail": "Contact not found"}, status=400)
        if conversation is None and accessible_department_ids(request.tenant_context.membership, "sales.operate") is not None:
            return Response({"detail": "Department-scoped sale requires a conversation"}, status=403)

        occurred_at = parse_datetime(str(data.get("occurredAt", ""))) or timezone.now()
        try:
            sale = create_manual_sale(
                context=request.tenant_context,
                product=product,
                amount_minor=int(data.get("amountMinor", 0)),
                currency=str(data.get("currency", "RUB")),
                occurred_at=occurred_at,
                reason=str(data.get("reason", "")),
                contact=contact,
                conversation=conversation,
                external_sale_id=str(data.get("externalSaleId", "")),
                external_customer_id=str(data.get("externalCustomerId", "")),
                line_items=data.get("lineItems") if isinstance(data.get("lineItems"), list) else None,
                metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
            )
        except SalesApiError as error:
            return _api_error(error)
        except (TypeError, ValueError):
            return Response({"detail": "amountMinor must be an integer"}, status=400)

        record_audit_event(
            action="sales.manual_created",
            actor=request.user,
            organization=org,
            object_type="Sale",
            object_id=str(sale.id),
            request=request,
        )
        return Response({"sale": sale_payload(sale, with_events=True)}, status=201)


class SaleDetailView(_Base):
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "sales_department"
    required_capability = "sales.view"

    def get(self, request: Request, sale_id: int) -> Response:
        try:
            sale = sale_for_context(context=request.tenant_context, sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({"detail": "Sale not found"}, status=404)
        if not require_capability(request.tenant_context.membership, self.required_capability, sale):
            return Response({"detail": "Sale not found"}, status=404)
        return Response({"sale": sale_payload(sale, with_events=True)})


class SaleActionView(_Base):
    """Ручная корректировка/возврат/отмена (SPEC §7.1). Обычная capability уровня
    организации — OWNER и ADMIN (ADR-HUB-0027 этап 2).

    Физическое удаление продажи запрещено — ошибка исправляется новым событием.
    """

    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "sales_department"
    required_capability = "sales.correct"

    _ACTIONS = {
        "correct": SaleEventType.CORRECTED,
        "cancel": SaleEventType.CANCELLED,
        "partial-refund": SaleEventType.PARTIALLY_REFUNDED,
        "refund": SaleEventType.REFUNDED,
    }

    def post(self, request: Request, sale_id: int, action: str) -> Response:
        event_type = self._ACTIONS.get(action)
        if event_type is None:
            return Response({"detail": "Unknown action"}, status=404)
        try:
            sale = sale_for_context(context=request.tenant_context, sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({"detail": "Sale not found"}, status=404)
        if not require_capability(request.tenant_context.membership, self.required_capability, sale):
            return Response({"detail": "Sale not found"}, status=404)

        data = request.data
        amount_minor = None
        refunded_amount_minor = None
        try:
            if data.get("amountMinor") is not None:
                amount_minor = int(data["amountMinor"])
            if data.get("refundedAmountMinor") is not None:
                refunded_amount_minor = int(data["refundedAmountMinor"])
        except (TypeError, ValueError):
            return Response({"detail": "amount fields must be integers"}, status=400)

        try:
            sale = record_manual_action(
                context=request.tenant_context,
                sale=sale,
                event_type=event_type,
                reason=str(data.get("reason", "")),
                amount_minor=amount_minor,
                refunded_amount_minor=refunded_amount_minor,
            )
        except SalesApiError as error:
            return _api_error(error)

        record_audit_event(
            action=f"sales.manual_{action.replace('-', '_')}",
            actor=request.user,
            organization=self._org(request),
            object_type="Sale",
            object_id=str(sale.id),
            request=request,
        )
        return Response({"sale": sale_payload(sale, with_events=True)})


class AttributionTokenView(_Base):
    """Выпуск непрозрачного attribution token для ссылки покупки из диалога (SPEC §6.1)."""

    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "sales_department"
    required_capability = "sales.operate"

    def post(self, request: Request) -> Response:
        org = self._org(request)
        data = request.data
        conversation = Conversation.objects.filter(id=data.get("conversationId"), organization=org).select_related("contact", "channel", "connection").first()
        if conversation is None:
            return Response({"detail": "Conversation not found"}, status=400)
        if not require_capability(request.tenant_context.membership, self.required_capability, conversation):
            return Response({"detail": "Conversation not found"}, status=404)
        try:
            product = Product.objects.get(organization=org, code=str(data.get("productCode", "")))
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=400)

        actor_type = "EMPLOYEE"
        try:
            token, raw = issue_attribution_token(
                context=request.tenant_context,
                product=product,
                contact=conversation.contact,
                conversation=conversation,
                actor_type=actor_type,
                actor_id=str(request.user.id),
                metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
            )
        except SalesApiError as error:
            return _api_error(error)

        record_audit_event(
            action="sales.attribution_issued",
            actor=request.user,
            organization=org,
            object_type="AttributionToken",
            object_id=str(token.id),
            request=request,
        )
        # Открытый токен возвращается один раз — продукт сохраняет его server-side.
        return Response({"token": raw, "expiresAt": token.expires_at.isoformat()}, status=201)


class SalesAnalyticsView(_Base):
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "sales_department"
    required_capability = "sales.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        params = request.query_params
        data = sales_analytics(
            request.tenant_context,
            date_from=params.get("from") or None,
            date_to=params.get("to") or None,
        )
        return Response(data)
