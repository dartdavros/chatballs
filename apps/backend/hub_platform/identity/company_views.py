from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from hub_platform.identity.models import Department, EmployeeRole


def _require_authenticated_profile(request: HttpRequest):
    if not request.user.is_authenticated:
        return None, JsonResponse({"detail": "Authentication required"}, status=401)
    return request.user.employee_profile, None


def _department_payload(department: Department) -> dict[str, object]:
    employees = list(department.employees.select_related("user").all())
    operators = [employee for employee in employees if employee.role == EmployeeRole.OPERATOR]
    products = [link.product for link in department.product_links.select_related("product").order_by("product__name")]
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


@require_GET
def department_list_view(request: HttpRequest) -> JsonResponse:
    profile, error = _require_authenticated_profile(request)
    if error is not None:
        return error
    departments = Department.objects.filter(organization=profile.organization).order_by("name")
    if profile.role == EmployeeRole.OPERATOR:
        departments = departments.filter(id=profile.department_id)
    return JsonResponse({"items": [_department_payload(department) for department in departments]})
