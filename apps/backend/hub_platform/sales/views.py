from __future__ import annotations

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import IsManager
from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.permissions import is_owner, is_sales_operator
from hub_platform.products.models import Product
from hub_platform.sales.analytics import sales_analytics
from hub_platform.sales.models import Sale, SaleEventType
from hub_platform.sales.selectors import (
    apply_sale_filters,
    sale_for_organization,
    sales_for_organization,
)
from hub_platform.sales.serializers import sale_payload
from hub_platform.sales.services import (
    SalesApiError,
    create_manual_sale,
    issue_attribution_token,
    record_manual_action,
    record_product_sales_event,
    resolve_sales_source_by_credential,
)


def _api_error(error: SalesApiError) -> Response:
    return Response({"detail": error.message, "error": error.error_code}, status=error.status_code)


def _bearer(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :].strip()
    return ""


class ProductSalesEventView(APIView):
    """Канонический вход Product Sales API (SPEC-HUB-0014 §4).

    Аутентификация — Bearer-ключ конкретного SalesSource, без пользовательской
    сессии. Идемпотентно по (source, event_id).
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []  # только Bearer источника, не сессия пользователя

    def post(self, request: Request) -> Response:
        source = resolve_sales_source_by_credential(_bearer(request))
        if source is None:
            return Response({"detail": "Invalid or revoked credential", "error": "invalid_credential"}, status=401)

        try:
            result = record_product_sales_event(source=source, payload=request.data)
        except SalesApiError as error:
            record_audit_event(
                action="sales.event_rejected",
                actor=None,
                organization=source.organization,
                object_type="SalesSource",
                object_id=str(source.id),
                payload={"error": error.error_code},
                request=request,
            )
            return _api_error(error)

        body = {"accepted": True, "duplicate": result.duplicate, "event_id": result.event.external_event_id}
        return Response(body, status=200 if result.duplicate else 202)


class _Base(APIView):
    def _org(self, request: Request):
        return request.user.employee_profile.organization


class SaleListCreateView(_Base):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = apply_sale_filters(sales_for_organization(self._org(request).id), request.query_params)
        return Response({"items": [sale_payload(sale) for sale in qs]})

    def post(self, request: Request) -> Response:
        # Ручная фиксация (SPEC §7). AI не создаёт ручную продажу; OWNER/оператор — да.
        if not is_sales_operator(request.user):
            return Response({"detail": "Not allowed"}, status=403)
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
        if data.get("contactId"):
            contact = Contact.objects.filter(id=data.get("contactId"), organization=org).first()
            if contact is None:
                return Response({"detail": "Contact not found"}, status=400)

        occurred_at = parse_datetime(str(data.get("occurredAt", ""))) or timezone.now()
        try:
            sale = create_manual_sale(
                organization=org,
                actor_user=request.user,
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
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, sale_id: int) -> Response:
        try:
            sale = sale_for_organization(organization_id=self._org(request).id, sale_id=sale_id)
        except Sale.DoesNotExist:
            return Response({"detail": "Sale not found"}, status=404)
        return Response({"sale": sale_payload(sale, with_events=True)})


class SaleActionView(_Base):
    """Ручная корректировка/возврат/отмена (SPEC §7.1). Обычная capability уровня
    организации — OWNER и ADMIN (ADR-HUB-0027 этап 2).

    Физическое удаление продажи запрещено — ошибка исправляется новым событием.
    """

    permission_classes = [IsManager]

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
            sale = sale_for_organization(organization_id=self._org(request).id, sale_id=sale_id)
        except Sale.DoesNotExist:
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
                sale=sale,
                actor_user=request.user,
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

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        org = self._org(request)
        data = request.data
        conversation = Conversation.objects.filter(id=data.get("conversationId"), organization=org).select_related("contact", "channel", "connection").first()
        if conversation is None:
            return Response({"detail": "Conversation not found"}, status=400)
        try:
            product = Product.objects.get(organization=org, code=str(data.get("productCode", "")))
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=400)

        actor_type = "OWNER" if is_owner(request.user) else "OPERATOR"
        try:
            token, raw = issue_attribution_token(
                organization=org,
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
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        params = request.query_params
        data = sales_analytics(
            self._org(request).id,
            date_from=params.get("from") or None,
            date_to=params.get("to") or None,
        )
        return Response(data)
