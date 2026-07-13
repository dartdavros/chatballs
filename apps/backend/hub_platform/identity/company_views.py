from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgent
from hub_platform.api.permissions import HasCapability
from hub_platform.identity.models import Department, EmployeeProfile
from hub_platform.identity.policy import ResourceScope, accessible_department_ids, authorize


def _department_payload(department: Department) -> dict[str, object]:
    employees = list(
        EmployeeProfile.objects.filter(organization=department.organization).select_related("user")
    )
    department_members = [
        employee for employee in employees if employee.primary_department_id == department.id
    ]
    operators = [
        employee
        for employee in employees
        if authorize(
            employee.user,
            "conversations.operate",
            ResourceScope(department.organization_id, department.id),
        )
    ]
    products = [link.product for link in department.product_links.select_related("product").order_by("product__name")]
    # AI-агенты отдела: AIAgent живёт на канале обработки (ADR-HUB-0019),
    # канал принадлежит отделу. Считаем активных агентов каналов этого отдела.
    agent_count = AIAgent.objects.filter(channel__department=department).count()
    return {
        "id": department.id,
        "code": department.code,
        "name": department.name,
        "status": department.status,
        "memberCount": len(department_members),
        "operatorCount": len(operators),
        "activeOperatorCount": len(
            [employee for employee in operators if employee.user.is_active and not employee.is_blocked]
        ),
        "agentCount": agent_count,
        "products": [{"code": product.code, "name": product.name} for product in products],
    }


class DepartmentListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "departments.view"

    def get(self, request: Request) -> Response:
        profile = request.user.employee_profile
        departments = Department.objects.filter(organization=profile.organization).order_by("name")
        department_ids = accessible_department_ids(request.user, self.required_capability)
        if department_ids is not None:
            departments = departments.filter(id__in=department_ids)
        return Response({"items": [_department_payload(department) for department in departments]})
