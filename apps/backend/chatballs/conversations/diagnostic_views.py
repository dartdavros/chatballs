from django.http import JsonResponse
from rest_framework.response import Response

from chatballs.conversations.diagnostic_export import conversation_diagnostic
from chatballs.conversations.models import Conversation
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


class ConversationDiagnosticView(ConversationViewBase):
    required_capability = "conversations.diagnostics"

    def get(self, request, conversation_id):
        try:
            conversation = self._conversation(request, conversation_id, self.required_capability)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        payload = conversation_diagnostic(conversation)
        self._audit(request, "diagnostic_exported", conversation)
        response = JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "indent": 2})
        response["Content-Disposition"] = f'attachment; filename="chatballs-dialog-{conversation.id}-diagnostic.json"'
        response["Cache-Control"] = "no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
