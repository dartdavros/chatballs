from rest_framework.response import Response

from chatballs.integrations.execution.lookup_queries import approval
from chatballs.integrations.execution.views import RunAPIView
from chatballs.tenancy.database import tenant_atomic


class ApprovalLookupView(RunAPIView):
    tenant_manages_own_transaction = True

    def initial(self, request, *args, **kwargs):
        with tenant_atomic(request.tenant_context):
            super().initial(request, *args, **kwargs)

    def get(self, request, public_id):
        return Response(approval(request.tenant_context, public_id, request.query_params))
