from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event
from hub_platform.products.models import Product, ProductStatus
from hub_platform.products.selectors import product_for_context, products_for_context
from hub_platform.products.serializers import product_payload
from hub_platform.products.services import ProductInput, create_product, set_product_status, update_product
def _input(body: dict[str, object], *, current: Product | None = None) -> ProductInput:
    return ProductInput(
        code=str(body.get("code", current.code if current else "")),
        name=str(body.get("name", current.name if current else "")),
        site_url=str(body.get("siteUrl", current.site_url if current else "")),
    )


def _validation_error(error: Exception) -> Response:
    if isinstance(error, ValidationError):
        if hasattr(error, "message_dict"):
            detail = "; ".join(message for messages in error.message_dict.values() for message in messages)
        else:
            detail = "; ".join(error.messages)
    else:
        detail = "Product code already exists"
    return Response({"detail": detail}, status=400)


class ProductListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.view"

    def get(self, request: Request) -> Response:
        products = products_for_context(request.tenant_context)
        return Response({"items": [product_payload(product) for product in products]})


class ProductCreateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"

    def post(self, request: Request) -> Response:
        profile = request.tenant_context.membership
        data = _input(request.data)
        try:
            product = create_product(context=request.tenant_context, data=data)
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        record_audit_event(
            action="products.product_created",
            actor=request.user,
            organization=profile.organization,
            object_type="Product",
            object_id=str(product.id),
            request=request,
        )
        product = product_for_context(context=request.tenant_context, product_id=product.id)
        return Response({"product": product_payload(product)}, status=201)


class ProductDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.view"

    def get(self, request: Request, product_id: int) -> Response:
        try:
            product = product_for_context(context=request.tenant_context, product_id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
        return Response({"product": product_payload(product)})


class ProductUpdateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"

    def patch(self, request: Request, product_id: int) -> Response:
        profile = request.tenant_context.membership
        try:
            product = product_for_context(context=request.tenant_context, product_id=product_id)
            data = _input(request.data, current=product)
            product = update_product(
                context=request.tenant_context, product=product, data=data
            )
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        record_audit_event(
            action="products.product_updated",
            actor=request.user,
            organization=profile.organization,
            object_type="Product",
            object_id=str(product.id),
            request=request,
        )
        product = product_for_context(context=request.tenant_context, product_id=product.id)
        return Response({"product": product_payload(product)})


class ProductStatusView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"
    status_value: ProductStatus

    def post(self, request: Request, product_id: int) -> Response:
        profile = request.tenant_context.membership
        try:
            product = Product.objects.get(id=product_id, organization=profile.organization)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
        set_product_status(
            context=request.tenant_context, product=product, status=self.status_value
        )
        record_audit_event(
            action=f"products.product_{self.status_value.lower()}",
            actor=request.user,
            organization=profile.organization,
            object_type="Product",
            object_id=str(product.id),
            request=request,
        )
        product = product_for_context(context=request.tenant_context, product_id=product.id)
        return Response({"product": product_payload(product)})


class ProductActivateView(ProductStatusView):
    status_value = ProductStatus.ACTIVE


class ProductDeactivateView(ProductStatusView):
    status_value = ProductStatus.DISABLED
