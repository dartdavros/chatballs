from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import IsManager
from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.audit import record_audit_event
from hub_platform.orders.models import Order
from hub_platform.orders.selectors import order_for_organization, orders_for_organization
from hub_platform.orders.serializers import order_payload
from hub_platform.orders.services import (
    IngestItemInput,
    OrderItemInput,
    cancel_order,
    create_order,
    ingest_order,
    mark_paid,
    resolve_product_by_token,
    set_fulfillment,
)


def _validation_error(error: ValidationError) -> Response:
    detail = "; ".join(m for ms in error.message_dict.values() for m in ms) if hasattr(error, "message_dict") else "; ".join(error.messages)
    return Response({"detail": detail}, status=400)


class _Base(APIView):
    def _org(self, request: Request):
        return request.user.employee_profile.organization

    def _audit(self, request: Request, action: str, order: Order) -> None:
        record_audit_event(
            action=f"orders.{action}",
            actor=request.user,
            organization=self._org(request),
            object_type="Order",
            object_id=str(order.id),
            request=request,
        )


class OrderListCreateView(_Base):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        orders = orders_for_organization(self._org(request).id)
        status_filter = request.query_params.get("paymentStatus")
        if status_filter:
            orders = orders.filter(payment_status=status_filter)
        contact_id = request.query_params.get("contact")
        if contact_id:
            orders = orders.filter(contact_id=contact_id)
        return Response({"items": [order_payload(order) for order in orders]})

    def post(self, request: Request) -> Response:
        org = self._org(request)
        raw_items = request.data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            return Response({"detail": "items must be a non-empty list"}, status=400)
        try:
            items = [
                OrderItemInput(offer_id=int(item["offerId"]), price_id=(int(item["priceId"]) if item.get("priceId") else None), quantity=int(item.get("quantity", 1)))
                for item in raw_items
            ]
        except (KeyError, TypeError, ValueError):
            return Response({"detail": "Each item needs offerId"}, status=400)
        try:
            contact = Contact.objects.get(id=int(request.data.get("contactId", 0)), organization=org)
        except (Contact.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Contact not found"}, status=400)
        try:
            order = create_order(organization=org, contact=contact, items=items)
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "created", order)
        order = order_for_organization(organization_id=org.id, order_id=order.id)
        return Response({"order": order_payload(order, with_items=True)}, status=201)


class OrderIngestView(APIView):
    # Вебхук бэкенда продукта (ADR-HUB-0018). Аутентификация — токеном продукта,
    # без пользовательской сессии. Идемпотентно по externalId.
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token = request.headers.get("X-Product-Token", "")
        product = resolve_product_by_token(token)
        if product is None:
            return Response({"detail": "Invalid product token"}, status=401)

        raw_items = request.data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            return Response({"detail": "items must be a non-empty list"}, status=400)
        try:
            items = [IngestItemInput(offer_code=str(item["offerCode"]), quantity=int(item.get("quantity", 1))) for item in raw_items]
        except (KeyError, TypeError, ValueError):
            return Response({"detail": "Each item needs offerCode"}, status=400)

        conversation = None
        conversation_id = request.data.get("conversationId")
        if conversation_id is not None:
            conversation = Conversation.objects.filter(id=conversation_id, organization=product.organization).first()
            if conversation is None:
                return Response({"detail": "Conversation not found"}, status=400)

        amount_raw = request.data.get("amountMinor")
        try:
            amount_minor = int(amount_raw) if amount_raw is not None else None
        except (TypeError, ValueError):
            return Response({"detail": "amountMinor must be an integer"}, status=400)

        try:
            order, created = ingest_order(
                product=product,
                external_id=str(request.data.get("externalId", "")).strip(),
                items=items,
                payment_status=str(request.data.get("paymentStatus", "PAID")),
                currency=str(request.data.get("currency", "RUB")),
                amount_minor=amount_minor,
                conversation=conversation,
                contact_name=str(request.data.get("contactName", "")).strip(),
            )
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action="orders.ingested" if created else "orders.ingest_duplicate",
            actor=None,
            organization=product.organization,
            object_type="Order",
            object_id=str(order.id),
            request=request,
        )
        return Response({"order": order_payload(order, with_items=True)}, status=201 if created else 200)


class OrderDetailView(_Base):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, order_id: int) -> Response:
        try:
            order = order_for_organization(organization_id=self._org(request).id, order_id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        return Response({"order": order_payload(order, with_items=True)})


class _OrderActionView(_Base):
    permission_classes = [IsManager]

    def _order(self, request: Request, order_id: int) -> Order:
        return order_for_organization(organization_id=self._org(request).id, order_id=order_id)


class OrderMarkPaidView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        mark_paid(order=order)
        self._audit(request, "paid", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})


class OrderCancelView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        cancel_order(order=order)
        self._audit(request, "cancelled", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})


class OrderFulfillmentView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        try:
            set_fulfillment(order=order, status=str(request.data.get("fulfillmentStatus", "")))
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "fulfillment_set", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})
