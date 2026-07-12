from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgent
from hub_platform.identity.models import Department, EmployeeRole


def _department_payload(department: Department) -> dict[str, object]:
    employees = list(department.employees.select_related("user").all())
    operators = [employee for employee in employees if employee.role == EmployeeRole.EMPLOYEE]
    products = [link.product for link in department.product_links.select_related("product").order_by("product__name")]
    # AI-агенты отдела: AIAgent живёт на канале обработки (ADR-HUB-0019),
    # канал принадлежит отделу. Считаем активных агентов каналов этого отдела.
    agent_count = AIAgent.objects.filter(channel__department=department).count()
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
        "agentCount": agent_count,
        "products": [{"code": product.code, "name": product.name} for product in products],
    }


class DepartmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile = request.user.employee_profile
        departments = Department.objects.filter(organization=profile.organization).order_by("name")
        if profile.role == EmployeeRole.EMPLOYEE:
            departments = departments.filter(id=profile.primary_department_id)
        return Response({"items": [_department_payload(department) for department in departments]})
