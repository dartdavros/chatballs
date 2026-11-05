"""Self-service transitions and permission-scoped, paginated history."""

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.work_status_access import readable_membership, work_status_history
from chatballs.identity.work_status_payloads import operation_payload, status_payload
from chatballs.identity.work_status_services import change_work_status


class OwnWorkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        membership = readable_membership(context=request.tenant_context)
        return Response(status_payload(membership))

    def post(self, request):
        data = request.data
        if not isinstance(data, dict) or set(data) != {"status", "expectedVersion", "operationId"}:
            raise ValidationError(t("work_status.transition_fields"))
        operation = change_work_status(
            context=request.tenant_context, status=data["status"],
            expected_version=data["expectedVersion"], operation_id=data["operationId"],
        )
        return Response(operation_payload(operation))


class EmployeeWorkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        membership = readable_membership(context=request.tenant_context, user_id=user_id)
        return Response(status_payload(membership))


class WorkStatusHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        return Response(work_status_history(context=request.tenant_context,
            user_id=user_id, params=request.query_params))
