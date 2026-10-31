"""Only organization managers may change execution retention."""

from rest_framework.response import Response

from chatballs.integrations.execution.retention import policy_for, update_policy
from chatballs.integrations.execution.views import RunAPIView


def policy_payload(row):
    return {"stepDays": row.step_days, "journalDays": row.journal_days, "version": row.version,
            "effectiveAt": row.effective_at.isoformat() if row.effective_at else None}


class RunRetentionView(RunAPIView):
    def get(self, request):
        self.manager(request)
        return Response(policy_payload(policy_for(request.tenant_context)))

    def put(self, request):
        self.manager(request)
        data = request.data if isinstance(request.data, dict) else {}
        row = update_policy(request.tenant_context, step_days=data.get("stepDays"), journal_days=data.get("journalDays"),
            version=data.get("version"), confirmed=data.get("confirmed", False))
        return Response(policy_payload(row))
