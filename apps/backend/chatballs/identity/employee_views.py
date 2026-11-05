from django.http import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.employee_api import response_for
from chatballs.identity.employee_creation import create_employee
from chatballs.identity.employee_queries import employee_avatar, employee_detail, list_employees


class EmployeeAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        avatar, content_type = employee_avatar(request.tenant_context, user_id)
        response = FileResponse(avatar.open("rb"), content_type=content_type, filename="avatar")
        response["Cache-Control"] = "private, max-age=86400"
        return response


class EmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(list_employees(request.tenant_context, request.query_params))


class EmployeeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return response_for(create_employee(request.tenant_context, request.data, request=request), success=201)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        return Response(employee_detail(request.tenant_context, user_id))
