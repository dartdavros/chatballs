"""Finalize an AI turn against current control state, inside tenant_atomic."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.ai.diagnostic_capture import finish_diagnostic
from chatballs.ai.execution_version import configuration_version
from chatballs.ai.runtime import HANDOFF_TOKEN
from chatballs.ai.turn import record_turn
from chatballs.conversations import ai_turn_result, tool_call_events
from chatballs.conversations.models import AiTurnState, Conversation, Message
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization


def refresh_turn_control(turn, context):
    organization = lock_organization(context.organization_id)
    # The network phase may have outlived a human takeover. Use the same lock
    # and fresh row for the check and for store_answer's subsequent updates.
    turn.conversation = Conversation.objects.select_for_update(of=("self",)).select_related(
        "contact", "connection", "channel__ai_agent",
    ).get(pk=turn.conversation.pk, organization_id=context.organization_id)
    turn.message = Message.objects.select_for_update().get(
        pk=turn.message.pk, organization_id=context.organization_id,
        conversation_id=turn.conversation.pk,
    )
    if (not autonomous_allowed(turn.conversation.channel, organization=organization,
                               connection=turn.conversation.connection, conversation=turn.conversation)
            or turn.mode_version != organization.operation_mode_version
            or turn.control_version != turn.conversation.ai_control_version
            or turn.agent.pk != getattr(getattr(turn.conversation.channel, "ai_agent", None), "pk", None)
            or configuration_version(turn.agent) != configuration_version(getattr(turn.conversation.channel, "ai_agent", None))
            or turn.message.ai_turn_state != AiTurnState.RUNNING):
        if turn.message.ai_turn_state == AiTurnState.RUNNING:
            turn.message.ai_turn_state = AiTurnState.DONE
            turn.message.save(update_fields=["ai_turn_state"])
        return False
    return True


def store_failure_if_current(*, turn, context, error):
    if not refresh_turn_control(turn, context):
        return ""
    return ai_turn_result.store_failure(turn=turn, context=context, error=error)


def finish_requested_turn(turn, context, plan, answer):
    current = refresh_turn_control(turn, context)
    run_ids = [call.action_result["runId"] for call in answer.tool_calls if call.action_result.get("runId")]
    if current and run_ids:
        from chatballs.integrations.execution.ai_reply import allowed
        current = allowed(context, turn.conversation.pk, run_ids)
        if current:
            turn.message.ai_delivery = {**turn.message.ai_delivery, "actionRuns": run_ids}
            turn.message.save(update_fields=["ai_delivery"])
        else:
            turn.message.ai_turn_state = AiTurnState.DONE
            turn.message.save(update_fields=["ai_turn_state"])
    finish_diagnostic(turn.message, plan, answer)
    reply = record_turn(agent=turn.agent, plan=plan, answer=answer)
    tool_call_events.record_tool_calls(turn.message, answer.tool_calls)
    if not current:
        return ""
    deadline = turn.message.created_at + timedelta(seconds=settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS)
    error = answer.error
    if timezone.now() >= deadline:
        error = "turn deadline passed"
    if error is not None:
        return ai_turn_result.store_failure(turn=turn, context=context, error=error)
    return ai_turn_result.store_answer(turn=turn, context=context, text=reply,
                                      prepared=answer.prepared_reply,
                                      handoff=bool(answer.result and HANDOFF_TOKEN in answer.result.text))
