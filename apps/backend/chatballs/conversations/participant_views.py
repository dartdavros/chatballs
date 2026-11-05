"""HTTP adapters for protected composition and participant settings."""

from rest_framework.response import Response

from chatballs.conversations.models import Conversation
from chatballs.conversations.participant_inputs import JoinInput, LeaveInput
from chatballs.conversations.participant_inputs import LimitInput as LimitInput
from chatballs.conversations.participant_payloads import member_payload as member_payload
from chatballs.conversations.participant_payloads import participant_payload
from chatballs.conversations.participant_queries import active_participants, participant_history
from chatballs.conversations.participant_services import add_participant, remove_participant
from chatballs.conversations.participant_settings import participant_limit
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t


def not_found():
    return Response({"detail": t("conversations.not_found")}, status=404)


class ParticipantListView(ConversationViewBase):
    required_capabilities = {"GET": "conversations.view", "POST": "conversations.participants"}

    def get(self, request, conversation_id):
        try:
            return Response(active_participants(request.tenant_context, conversation_id))
        except Conversation.DoesNotExist:
            return not_found()

    def post(self, request, conversation_id):
        data = JoinInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            participant, created = add_participant(context=request.tenant_context,
                conversation_id=conversation_id, membership_id=data.validated_data["membershipId"],
                reason=data.validated_data["reason"])
        except Conversation.DoesNotExist:
            return not_found()
        return Response({"participant": participant_payload(participant)}, status=201 if created else 200)


class ParticipantDetailView(ConversationViewBase):
    required_capability = "conversations.participants"

    def delete(self, request, conversation_id, participant_id):
        data = LeaveInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            participant, _ = remove_participant(context=request.tenant_context,
                conversation_id=conversation_id, participant_id=participant_id,
                reason=data.validated_data["reason"])
        except Conversation.DoesNotExist:
            return not_found()
        return Response({"participant": participant_payload(participant)})


class ParticipantHistoryView(ConversationViewBase):
    def get(self, request, conversation_id):
        try:
            return Response(participant_history(request.tenant_context, conversation_id, request.query_params))
        except Conversation.DoesNotExist:
            return not_found()


class ParticipantLimitView(ConversationViewBase):
    required_capabilities = {"GET": "conversations.view", "PATCH": "settings.manage"}

    def get(self, request):
        return Response(participant_limit(request.tenant_context))

    def patch(self, request):
        return Response(participant_limit(request.tenant_context, request.data, request=request))
