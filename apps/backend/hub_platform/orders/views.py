from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.conversations.models import Contact, Conversation
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import Organization
from hub_platform.orders.models import Order
from hub_platform.orders.selectors import order_for_context, orders_for_context
from hub_platform.orders.serializers import order_payload
from hub_platform.orders.services import (
    IngestItemInput,
    OrderItemInput,
    cancel_order,
    create_order,
    hash_ingest_token,
    ingest_order,
    mark_paid,
    set_fulfillment,
)
from hub_platform.products.models import Product
from hub_platform.identity.policy import accessible_department_ids, require_capability
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import product_ingest_route


def _validation_error(error: ValidationError) -> Response:
    detail = "; ".join(m for ms in error.message_dict.values() for m in ms) if hasattr(error, "message_dict") else "; ".join(error.messages)
    return Response({"detail": detail}, status=400)


class _Base(APIView):
    def _org(self, request: Request):
        return request.tenant_context.organization

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
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "sales.view", "POST": "sales.operate"}

    def get(self, request: Request) -> Response:
        orders = orders_for_context(request.tenant_context)
        department_ids = accessible_department_ids(request.tenant_context.membership, "sales.view")
        if department_ids is not None:
            orders = orders.filter(conversation__channel__department_id__in=department_ids)
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
        department_ids = accessible_department_ids(request.tenant_context.membership, "sales.operate")
        conversation = None
        if request.data.get("conversationId"):
            conversation = Conversation.objects.filter(
                id=request.data.get("conversationId"), organization=org, contact=contact
            ).select_related("channel").first()
            if conversation is None or not require_capability(
                request.tenant_context.membership, "sales.operate", conversation
            ):
                return Response({"detail": "Conversation not found"}, status=404)
        if department_ids is not None and conversation is None:
            return Response(
                {"detail": "Department-scoped order requires a conversation"}, status=403
            )
        try:
            order = create_order(
                context=request.tenant_context,
                contact=contact,
                items=items,
                conversation=conversation,
            )
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "created", order)
        order = order_for_context(context=request.tenant_context, order_id=order.id)
        return Response({"order": order_payload(order, with_items=True)}, status=201)


class OrderIngestView(APIView):
    # Вебхук бэкенда продукта (ADR-HUB-0018). Аутентификация — токеном продукта,
    # без пользовательской сессии. Идемпотентно по externalId.
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        token = request.headers.get("X-Product-Token", "")
        route = product_ingest_route(hash_ingest_token(token)) if token else None
        if route is None:
            return Response({"detail": "Invalid product token"}, status=401)
        try:
            organization = Organization.objects.get(pk=route.organization_id)
        except Organization.DoesNotExist:
            return Response({"detail": "Invalid product token"}, status=401)
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            product = Product.objects.filter(
                id=route.resource_id,
                organization=organization,
                ingest_token_hash=hash_ingest_token(token),
            ).first()
            if product is None:
                return Response({"detail": "Invalid product token"}, status=401)
            return self._post_for_product(request, context=context, product=product)

    def _post_for_product(
        self,
        request: Request,
        *,
        context: TenantContext,
        product: Product,
    ) -> Response:
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
                context=context,
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
    permission_classes = [HasCapability]
    required_capability = "sales.view"

    def get(self, request: Request, order_id: int) -> Response:
        try:
            order = order_for_context(context=request.tenant_context, order_id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        if not require_capability(request.tenant_context.membership, self.required_capability, order):
            return Response({"detail": "Order not found"}, status=404)
        return Response({"order": order_payload(order, with_items=True)})


class _OrderActionView(_Base):
    permission_classes = [HasCapability]
    required_capability = "sales.correct"

    def _order(self, request: Request, order_id: int) -> Order:
        order = order_for_context(context=request.tenant_context, order_id=order_id)
        if not require_capability(request.tenant_context.membership, self.required_capability, order):
            raise Order.DoesNotExist
        return order


class OrderMarkPaidView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        mark_paid(context=request.tenant_context, order=order)
        self._audit(request, "paid", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})


class OrderCancelView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        cancel_order(context=request.tenant_context, order=order)
        self._audit(request, "cancelled", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})


class OrderFulfillmentView(_OrderActionView):
    def post(self, request: Request, order_id: int) -> Response:
        try:
            order = self._order(request, order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
        try:
            set_fulfillment(
                context=request.tenant_context,
                order=order,
                status=str(request.data.get("fulfillmentStatus", "")),
            )
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "fulfillment_set", order)
        return Response({"order": order_payload(self._order(request, order_id), with_items=True)})
