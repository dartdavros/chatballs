"""Shared test-chat application operation; uses the real AI turn pipeline."""

import time

from django.conf import settings

from chatballs.ai.agent_card_queries import require
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.test_chat_data import parse_test_client_data
from chatballs.ai.turn import (
    plan_chat,
    plan_query_embedding,
    record_turn,
    run_query_embedding,
    run_turn_chat,
)
from chatballs.channels.models import Channel
from chatballs.channels.selectors import channel_for_context
from chatballs.conversations.tool_call_events import tool_call_payload
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic


def run_test_chat(context, agent_id, body):
    with tenant_atomic(context):
        require(context, "ai.manage")
    started = time.monotonic()
    calls = []
    actions = []
    skill_support, skill_warning = ("unknown", "")
    execution_mode = body.get("executionMode", "preview")
    if not isinstance(execution_mode, str) or execution_mode not in {"preview", "execute"}:
        return (400, {"detail": t("ai.test_client_data_invalid")})
    message = body.get("message", "")
    if not isinstance(message, str) or not message.strip():
        return (400, {"detail": t("ai.empty_message")})
    history = body.get("history", [])
    if not isinstance(history, list) or any(
        not isinstance(item, dict)
        or item.get("role") not in {"user", "assistant"}
        or (not isinstance(item.get("content"), str))
        for item in history
    ):
        return (400, {"detail": t("ai.history_must_be_list")})
    try:
        with tenant_atomic(context):
            try:
                channel = channel_for_context(
                    context=context, channel_id=agent_id, capability="ai.view"
                )
            except Channel.DoesNotExist:
                return (404, {"detail": t("ai.agent_not_found")})
            agent = getattr(channel, "ai_agent", None)
            if agent is None or not agent.is_active:
                raise ProviderError(t("channels.no_active_agent"))
            data = parse_test_client_data(channel, body.get("clientData"))
            history = history[-agent.history_limit :] if agent.history_limit else []
            embedding_job = plan_query_embedding(
                agent=agent, query=message.strip(), pseudonymizer=data.pseudonymizer
            )
        embedding = run_query_embedding(embedding_job)
        with tenant_atomic(context):
            plan = plan_chat(
                agent=agent,
                message=message.strip(),
                history=history,
                embedding=embedding,
                pseudonymizer=data.pseudonymizer,
                client=data.client,
                client_context=data.context_fields,
                test_tenant=context,
                action_preview=execution_mode == "preview",
            )
            skill_support = plan.skills.support
            if plan.skills.items and skill_support == "unsupported":
                skill_warning = t("skills.model_unsupported")
        answer = run_turn_chat(
            plan, time_left=settings.CHATBALLS_AI_TURN_TIMEOUT - (time.monotonic() - started)
        )
        with tenant_atomic(context):
            reply = record_turn(agent=agent, plan=plan, answer=answer)
        calls = [
            {
                "name": call.name,
                **tool_call_payload(
                    {"tool": call.title, "error": call.error, "durationMs": call.duration_ms}
                ),
            }
            for call in answer.tool_calls
        ]
        actions = [call.action_result for call in answer.tool_calls if call.action_result]
        if answer.error is not None:
            raise answer.error
    except ProviderError as error:
        return (
            502,
            {
                "detail": t("ai.provider_error", error=error),
                "toolCalls": calls,
                "serviceActions": actions,
                "skillSupport": skill_support,
                "skillWarning": skill_warning,
            },
        )
    result = answer.result
    return (
        200,
        {
            "serviceActions": actions,
            "reply": reply,
            **(
                {"formatVersion": 1, **answer.prepared_reply.payload()}
                if answer.prepared_reply
                else {}
            ),
            "model": result.model,
            "promptTokens": sum(item.result.prompt_tokens for item in answer.rounds if item.result)
            if answer.rounds
            else result.prompt_tokens,
            "completionTokens": sum(
                item.result.completion_tokens for item in answer.rounds if item.result
            )
            if answer.rounds
            else result.completion_tokens,
            "toolCalls": calls,
            "skillSupport": skill_support,
            "skillWarning": skill_warning,
        },
    )
