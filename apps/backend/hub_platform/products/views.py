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
from hub_platform.identity.policy import accessible_department_ids


def _department_ids(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
        raise ValidationError({"departmentIds": "List of department IDs required"})
    return tuple(value)


def _input(body: dict[str, object], *, current: Product | None = None) -> ProductInput:
    current_departments = [link.department_id for link in current.department_links.all()] if current else []
    return ProductInput(
        code=str(body.get("code", current.code if current else "")),
        name=str(body.get("name", current.name if current else "")),
        site_url=str(body.get("siteUrl", current.site_url if current else "")),
        department_ids=_department_ids(body.get("departmentIds", current_departments)),
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


def _departments_allowed(request: Request, capability: str, department_ids) -> bool:
    accessible = accessible_department_ids(request.tenant_context.membership, capability)
    return accessible is None or set(department_ids).issubset(accessible)


def _product_allowed(request: Request, capability: str, product: Product) -> bool:
    accessible = accessible_department_ids(request.tenant_context.membership, capability)
    return accessible is None or product.department_links.filter(
        department_id__in=accessible
    ).exists()


class ProductListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.view"

    def get(self, request: Request) -> Response:
        products = products_for_context(request.tenant_context)
        department_ids = accessible_department_ids(request.tenant_context.membership, self.required_capability)
        if department_ids is not None:
            products = products.filter(department_links__department_id__in=department_ids).distinct()
        return Response({"items": [product_payload(product) for product in products]})


class ProductCreateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"

    def post(self, request: Request) -> Response:
        profile = request.tenant_context.membership
        data = _input(request.data)
        if not _departments_allowed(request, self.required_capability, data.department_ids):
            return Response({"detail": "Product departments are outside access scope"}, status=403)
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
        profile = request.tenant_context.membership
        try:
            product = product_for_context(context=request.tenant_context, product_id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=404)
        if not _product_allowed(request, self.required_capability, product):
            return Response({"detail": "Product not found"}, status=404)
        return Response({"product": product_payload(product)})


class ProductUpdateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"

    def patch(self, request: Request, product_id: int) -> Response:
        profile = request.tenant_context.membership
        try:
            product = product_for_context(context=request.tenant_context, product_id=product_id)
            if not _product_allowed(request, self.required_capability, product):
                raise Product.DoesNotExist
            data = _input(request.data, current=product)
            if not _departments_allowed(request, self.required_capability, data.department_ids):
                return Response(
                    {"detail": "Product departments are outside access scope"}, status=403
                )
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
        if not _product_allowed(request, self.required_capability, product):
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
