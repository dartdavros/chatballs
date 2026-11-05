from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.pagination import page_payload, paginate
from chatballs.api.permissions import HasCapability
from chatballs.conversations.transfer_reason_inputs import ReasonInput
from chatballs.conversations.transfer_reason_payloads import (
    reason_option_payload as reason_option_payload,
)
from chatballs.conversations.transfer_reason_payloads import reason_payload
from chatballs.conversations.transfer_services import (
    disable_reason,
    reasons_for_management,
    save_reason,
)
from chatballs.i18n import t


class ReasonListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.manage"

    def get(self, request):
        reasons = reasons_for_management(request.tenant_context)
        return Response(page_payload(paginate(reasons, request.query_params), reason_payload))

    def post(self, request):
        serializer = ReasonInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = save_reason(context=request.tenant_context, data=serializer.validated_data)
        reason = reasons_for_management(request.tenant_context).get(pk=reason.pk)
        return Response({"reason": reason_payload(reason)}, status=201)


class ReasonDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.manage"

    def get(self, request, reason_id):
        reason = reasons_for_management(request.tenant_context).filter(pk=reason_id).first()
        if reason is None:
            return Response({"detail": t("transfers.reason_not_found")}, status=404)
        return Response({"reason": reason_payload(reason)})

    def patch(self, request, reason_id):
        serializer = ReasonInput(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reason = save_reason(
            context=request.tenant_context, reason_id=reason_id, data=serializer.validated_data
        )
        reason = reasons_for_management(request.tenant_context).get(pk=reason.pk)
        return Response({"reason": reason_payload(reason)})

    def delete(self, request, reason_id):
        disable_reason(context=request.tenant_context, reason_id=reason_id)
        return Response(status=204)
