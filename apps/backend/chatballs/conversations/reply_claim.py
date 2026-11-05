
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.conversations.models import Conversation
from chatballs.conversations.reply_claim_service import claim_reply as claim_reply
from chatballs.conversations.services import ClaimError
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


def claim_for_reply(view: ConversationViewBase, request: Request, conversation: Conversation) -> Conversation | Response:
    try:
        return claim_reply(context=request.tenant_context, conversation_id=conversation.pk,
            operation_id=request.headers.get("Idempotency-Key"), request=request)
    except Conversation.DoesNotExist:
        return Response({"detail": t("conversations.not_found")}, status=404)
    except ClaimError as error:
        return Response({"detail": str(error)}, status=409)
