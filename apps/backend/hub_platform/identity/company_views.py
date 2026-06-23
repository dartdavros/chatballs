from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.models import Department, EmployeeRole


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


class DepartmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile = request.user.employee_profile
        departments = Department.objects.filter(organization=profile.organization).order_by("name")
        if profile.role == EmployeeRole.OPERATOR:
            departments = departments.filter(id=profile.department_id)
        return Response({"items": [_department_payload(department) for department in departments]})
