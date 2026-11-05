from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity.employee_api import response_for
from chatballs.identity.employee_updates import update_employee


class EmployeeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        return response_for(update_employee(request.tenant_context, user_id, request.data, request=request))
