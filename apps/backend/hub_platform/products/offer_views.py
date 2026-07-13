from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils.dateparse import parse_datetime
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.policy import accessible_department_ids
from hub_platform.products.models import Offer, Product
from hub_platform.products.selectors import product_for_organization
from hub_platform.products.serializers import product_payload
from hub_platform.products.services import (
    OfferInput,
    PriceInput,
    add_price_version,
    create_offer,
    update_offer,
)
from hub_platform.products.views import _validation_error


def _bool(value: object, default: bool) -> bool:
    return bool(value) if value is not None else default


def _offer_input(body: dict[str, object], *, current: Offer | None = None) -> OfferInput:
    box_id = body.get("primaryBoxOfferId", current.primary_box_offer_id if current else None)
    return OfferInput(
        code=str(body.get("code", current.code if current else "")),
        name=str(body.get("name", current.name if current else "")),
        description=str(body.get("description", current.description if current else "")),
        fulfillment_type=str(body.get("fulfillmentType", current.fulfillment_type if current else "")),
        payment_type=str(body.get("paymentType", current.payment_type if current else "")),
        is_active=_bool(body.get("isActive"), current.is_active if current else True),
        ai_offerable=_bool(body.get("aiOfferable"), current.ai_offerable if current else False),
        primary_box_offer_id=int(box_id) if box_id not in (None, "") else None,
    )


class _ProductScopedView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"

    def _product(self, request: Request, product_id: int) -> Product:
        product = product_for_organization(
            organization_id=request.user.employee_profile.organization_id, product_id=product_id
        )
        department_ids = accessible_department_ids(request.user, self.required_capability)
        if department_ids is not None and not product.department_links.filter(
            department_id__in=department_ids
        ).exists():
            raise Product.DoesNotExist
        return product

    def _audit(self, request: Request, action: str, object_type: str, object_id: int) -> None:
        record_audit_event(
            action=action,
            actor=request.user,
            organization=request.user.employee_profile.organization,
            object_type=object_type,
            object_id=str(object_id),
            request=request,
        )

    def _reloaded(self, request: Request, product_id: int) -> Response:
        product = self._product(request, product_id)
        return Response({"product": product_payload(product)})


class OfferCreateView(_ProductScopedView):
    def post(self, request: Request, product_id: int) -> Response:
        try:
            product = self._product(request, product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
        try:
            offer = create_offer(product=product, data=_offer_input(request.data))
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        self._audit(request, "products.offer_created", "Offer", offer.id)
        return Response({"product": product_payload(self._product(request, product_id))}, status=201)


class OfferUpdateView(_ProductScopedView):
    def patch(self, request: Request, product_id: int, offer_id: int) -> Response:
        try:
            product = self._product(request, product_id)
            offer = Offer.objects.get(product=product, id=offer_id)
        except (Product.DoesNotExist, Offer.DoesNotExist):
            return Response({"detail": "Offer not found"}, status=404)
        try:
            update_offer(offer=offer, data=_offer_input(request.data, current=offer))
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        self._audit(request, "products.offer_updated", "Offer", offer.id)
        return self._reloaded(request, product_id)


class PriceCreateView(_ProductScopedView):
    def post(self, request: Request, product_id: int, offer_id: int) -> Response:
        try:
            product = self._product(request, product_id)
            offer = Offer.objects.get(product=product, id=offer_id)
        except (Product.DoesNotExist, Offer.DoesNotExist):
            return Response({"detail": "Offer not found"}, status=404)
        body = request.data
        try:
            amount_minor = int(body.get("amountMinor"))
        except (TypeError, ValueError):
            return Response({"detail": "amountMinor must be an integer"}, status=400)
        valid_from_raw = body.get("validFrom")
        price_input = PriceInput(
            amount_minor=amount_minor,
            billing_period=str(body.get("billingPeriod", "")),
            currency=str(body.get("currency", "RUB")),
            valid_from=parse_datetime(valid_from_raw) if valid_from_raw else None,
        )
        try:
            price = add_price_version(offer=offer, data=price_input)
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        self._audit(request, "products.price_version_added", "Price", price.id)
        return Response({"product": product_payload(self._product(request, product_id))}, status=201)
