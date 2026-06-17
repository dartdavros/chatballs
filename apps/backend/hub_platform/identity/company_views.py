import json

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.employee_views import owner_required
from hub_platform.identity.models import (
    AuditResult,
    Department,
    EmployeeRole,
    Product,
    ProductStatus,
)


def _json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


def _require_authenticated_profile(request: HttpRequest):
    if not request.user.is_authenticated:
        return None, JsonResponse({"detail": "Authentication required"}, status=401)
    return request.user.employee_profile, None


def _department_payload(department: Department) -> dict[str, object]:
    employees = list(department.employees.select_related("user").all())
    operators = [employee for employee in employees if employee.role == EmployeeRole.OPERATOR]
    products = list(department.organization.products.order_by("name"))
    return {
        "id": department.id,
        "code": department.code,
        "name": department.name,
        "status": department.status,
        "memberCount": len(employees),
        "operatorCount": len(operators),
        "activeOperatorCount": len(
            [employee for employee in operators if employee.user.is_active and not employee.is_blocked]
        ),
        "products": [{"code": product.code, "name": product.name} for product in products],
    }


def _product_payload(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "status": product.status,
        "siteUrl": product.site_url,
        "createdAt": product.created_at.isoformat(),
    }


@require_GET
def department_list_view(request: HttpRequest) -> JsonResponse:
    profile, error = _require_authenticated_profile(request)
    if error is not None:
        return error
    departments = Department.objects.filter(organization=profile.organization).order_by("name")
    if profile.role == EmployeeRole.OPERATOR:
        departments = departments.filter(id=profile.department_id)
    return JsonResponse({"items": [_department_payload(department) for department in departments]})


@require_GET
def product_list_view(request: HttpRequest) -> JsonResponse:
    profile, error = _require_authenticated_profile(request)
    if error is not None:
        return error
    products = Product.objects.filter(organization=profile.organization).order_by("name")
    return JsonResponse({"items": [_product_payload(product) for product in products]})


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def create_product_view(request: HttpRequest) -> JsonResponse:
    owner_profile = request.user.employee_profile
    body = _json_body(request)
    code = str(body.get("code", "")).strip().lower()
    name = str(body.get("name", "")).strip()
    site_url = str(body.get("siteUrl", "")).strip()
    if not code:
        return JsonResponse({"detail": "Product code is required"}, status=400)
    if not name:
        return JsonResponse({"detail": "Product name is required"}, status=400)
    product = Product.objects.create(
        organization=owner_profile.organization,
        code=code,
        name=name,
        site_url=site_url,
    )
    record_audit_event(
        action="identity.product_created",
        actor=request.user,
        organization=owner_profile.organization,
        object_type="Product",
        object_id=str(product.id),
        request=request,
    )
    return JsonResponse({"product": _product_payload(product)}, status=201)


@csrf_protect
@require_POST
@owner_required
@transaction.atomic
def deactivate_product_view(request: HttpRequest, product_id: int) -> JsonResponse:
    owner_profile = request.user.employee_profile
    try:
        product = Product.objects.get(id=product_id, organization=owner_profile.organization)
    except Product.DoesNotExist:
        return JsonResponse({"detail": "Product not found"}, status=404)
    product.status = ProductStatus.DISABLED
    product.save(update_fields=["status"])
    record_audit_event(
        action="identity.product_deactivated",
        actor=request.user,
        organization=owner_profile.organization,
        object_type="Product",
        object_id=str(product.id),
        result=AuditResult.SUCCESS,
        request=request,
    )
    return JsonResponse({"product": _product_payload(product)})
