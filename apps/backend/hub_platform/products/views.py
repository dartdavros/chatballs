import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_views import owner_required
from hub_platform.products.models import Product, ProductStatus
from hub_platform.products.selectors import product_for_organization, products_for_organization
from hub_platform.products.serializers import product_payload
from hub_platform.products.services import ProductInput, create_product, set_product_status, update_product


def _profile_or_error(request: HttpRequest):
    if not request.user.is_authenticated:
        return None, JsonResponse({"detail": "Authentication required"}, status=401)
    return request.user.employee_profile, None


def _json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ValidationError("Invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValidationError("JSON object required")
    return payload


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
        summary=str(body.get("summary", current.summary if current else "")),
        sales_description=str(body.get("salesDescription", current.sales_description if current else "")),
        department_ids=_department_ids(body.get("departmentIds", current_departments)),
    )


def _validation_error(error: Exception) -> JsonResponse:
    if isinstance(error, ValidationError):
        if hasattr(error, "message_dict"):
            detail = "; ".join(message for messages in error.message_dict.values() for message in messages)
        else:
            detail = "; ".join(error.messages)
    else:
        detail = "Product code already exists"
    return JsonResponse({"detail": detail}, status=400)


@require_GET
def product_list_view(request: HttpRequest) -> JsonResponse:
    profile, error = _profile_or_error(request)
    if error is not None:
        return error
    products = products_for_organization(profile.organization_id)
    return JsonResponse({"items": [product_payload(product) for product in products]})


@require_GET
def product_detail_view(request: HttpRequest, product_id: int) -> JsonResponse:
    profile, error = _profile_or_error(request)
    if error is not None:
        return error
    try:
        product = product_for_organization(organization_id=profile.organization_id, product_id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"detail": "Product not found"}, status=404)
    return JsonResponse({"product": product_payload(product)})


@csrf_protect
@require_POST
@owner_required
def create_product_view(request: HttpRequest) -> JsonResponse:
    profile = request.user.employee_profile
    try:
        product = create_product(organization=profile.organization, data=_input(_json_body(request)))
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
    product = product_for_organization(organization_id=profile.organization_id, product_id=product.id)
    return JsonResponse({"product": product_payload(product)}, status=201)


@csrf_protect
@require_http_methods(["PATCH"])
@owner_required
def update_product_view(request: HttpRequest, product_id: int) -> JsonResponse:
    profile = request.user.employee_profile
    try:
        product = product_for_organization(organization_id=profile.organization_id, product_id=product_id)
        product = update_product(product=product, data=_input(_json_body(request), current=product))
    except Product.DoesNotExist:
        return JsonResponse({"detail": "Product not found"}, status=404)
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
    product = product_for_organization(organization_id=profile.organization_id, product_id=product.id)
    return JsonResponse({"product": product_payload(product)})


def _change_status(request: HttpRequest, product_id: int, status: ProductStatus) -> JsonResponse:
    profile = request.user.employee_profile
    try:
        product = Product.objects.get(id=product_id, organization=profile.organization)
    except Product.DoesNotExist:
        return JsonResponse({"detail": "Product not found"}, status=404)
    set_product_status(product=product, status=status)
    record_audit_event(
        action=f"products.product_{status.lower()}",
        actor=request.user,
        organization=profile.organization,
        object_type="Product",
        object_id=str(product.id),
        request=request,
    )
    product = product_for_organization(organization_id=profile.organization_id, product_id=product.id)
    return JsonResponse({"product": product_payload(product)})


@csrf_protect
@require_POST
@owner_required
def activate_product_view(request: HttpRequest, product_id: int) -> JsonResponse:
    return _change_status(request, product_id, ProductStatus.ACTIVE)


@csrf_protect
@require_POST
@owner_required
def deactivate_product_view(request: HttpRequest, product_id: int) -> JsonResponse:
    return _change_status(request, product_id, ProductStatus.DISABLED)
