from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.models import Conversation
from chatballs.conversations.selectors import conversation_for_context
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import require_capability


class ConversationViewBase(APIView):
    permission_classes = [HasCapability]
    required_capability = "conversations.view"

    def _org(self, request: Request):
        return request.tenant_context.organization

    def _conversation(
        self,
        request: Request,
        conversation_id: int,
        capability: str = "conversations.view",
    ) -> Conversation:
        conversation = conversation_for_context(
            context=request.tenant_context, conversation_id=conversation_id
        )
        if not require_capability(
            request.tenant_context.membership, capability, conversation
        ):
            raise Conversation.DoesNotExist
        return conversation

    def _audit(
        self, request: Request, action: str, conversation: Conversation
    ) -> None:
        record_audit_event(
            action=f"conversations.{action}",
            actor=request.user,
            organization=self._org(request),
            object_type="Conversation",
            object_id=str(conversation.id),
            request=request,
        )
