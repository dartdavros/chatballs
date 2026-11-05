"""HTTP adapters for rule settings and the protected execution journal."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.rules import operations
from chatballs.conversations.rules.presentation import rule_payload as rule_payload


class RuleListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.view"

    def get(self, request):
        return Response(operations.list_rules(request.tenant_context))


class RuleDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.manage"

    def patch(self, request, kind):
        return Response(operations.change_rule(request.tenant_context, kind, request.data))


class RuleExecutionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(operations.rule_journal(request.tenant_context, request.query_params))
