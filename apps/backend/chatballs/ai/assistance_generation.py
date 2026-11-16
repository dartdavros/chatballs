"""At-most-once logical generation; all network calls are outside tenant transactions."""

from dataclasses import replace

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from chatballs.ai.assistance_access import reply_context
from chatballs.ai.assistance_history import history_snapshot
from chatballs.ai.assistance_models import ReplyAssistanceError as Error
from chatballs.ai.assistance_realtime import notify_suggestion
from chatballs.ai.models import ReplyAssistanceStatus as Status
from chatballs.ai.models import ReplySuggestion
from chatballs.ai.provider.base import ChatMessage, ProviderError
from chatballs.ai.runtime import HANDOFF_TOKEN, MESSENGER_STYLE_GUARD
from chatballs.ai.turn import (
    plan_chat,
    plan_query_embedding,
    record_turn,
    run_query_embedding,
    run_turn_chat,
    turn_pseudonymizer,
)
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


def time_left(suggestion):
    return (settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS
            - (timezone.now() - suggestion.created_at).total_seconds())


def finish(suggestion, *, text="", error=""):
    suggestion.status = Status.ERROR if error else Status.READY
    suggestion.error_code = error
    suggestion.original_text = "" if error else text
    suggestion.completed_at = timezone.now()
    suggestion.save(update_fields=["status", "error_code", "original_text", "completed_at"])
    if suggestion.position == 1:
        attempt = suggestion.attempt
        attempt.status = suggestion.status
        attempt.error_code = error
        attempt.completed_at = suggestion.completed_at
        attempt.save(update_fields=["status", "error_code", "completed_at"])
    notify_suggestion(suggestion)


def requester_context(context, suggestion):
    return TenantContext.for_membership(suggestion.requested_by)


def load_suggestion(context, public_id):
    from chatballs.conversations.models import Conversation

    target = ReplySuggestion.objects.filter(
        organization_id=context.organization_id, public_id=public_id,
    ).values_list("attempt__conversation_id", flat=True).first()
    if target is None:
        return None
    # All assistance mutations lock the conversation before the suggestion.
    if not Conversation.objects.select_for_update().filter(
        pk=target, organization_id=context.organization_id,
    ).exists():
        return None
    return ReplySuggestion.objects.select_for_update(of=("self",)).select_related(
        "attempt__agent__channel__organization", "requested_by__user",
        "requested_by__organization",
    ).filter(organization_id=context.organization_id, public_id=public_id).first()


def begin(context, public_id):
    suggestion = load_suggestion(context, public_id)
    if suggestion is None or suggestion.status in (Status.READY, Status.ERROR):
        return None
    if time_left(suggestion) <= 0:
        finish(suggestion, error=Error.TIMEOUT)
        return None
    if suggestion.status == Status.RUNNING:
        # A redelivered event after a worker crash must never call the model again.
        finish(suggestion, error=Error.GENERATION_FAILED)
        return None
    try:
        _, conversation = reply_context(requester_context(context, suggestion),
                                        suggestion.attempt.conversation_id)
    except APIException:
        finish(suggestion, error=Error.PERMISSION_DENIED)
        return None
    agent = suggestion.attempt.agent
    if not agent.assistance_enabled or conversation.channel_id != agent.channel_id:
        finish(suggestion, error=Error.PERMISSION_DENIED)
        return None
    if agent.provider_integration_id is None:
        finish(suggestion, error=Error.PROVIDER_UNAVAILABLE)
        return None
    history, query, version = history_snapshot(conversation, agent.history_limit)
    suggestion.status = Status.RUNNING
    suggestion.started_at = timezone.now()
    suggestion.history_version = version
    suggestion.save(update_fields=["status", "started_at", "history_version"])
    if suggestion.position == 1:
        attempt = suggestion.attempt
        attempt.status = Status.RUNNING
        attempt.started_at = suggestion.started_at
        attempt.history_version = version
        attempt.save(update_fields=["status", "started_at", "history_version"])
    notify_suggestion(suggestion)
    pseudonymizer = turn_pseudonymizer(conversation)
    embedding_job = plan_query_embedding(agent=agent, query=query, pseudonymizer=pseudonymizer, assistance=True)
    return suggestion, conversation, history, query, pseudonymizer, embedding_job


def run_requested_assistance(payload, context):
    public_id = payload["suggestionId"]
    with tenant_atomic(context):
        work = begin(context, public_id)
    if work is None:
        return
    suggestion, conversation, history, query, pseudonymizer, embedding_job = work
    agent = suggestion.attempt.agent
    try:
        embedding = run_query_embedding(embedding_job)
        with tenant_atomic(context):
            plan = plan_chat(
                agent=agent, message=query, history=history, embedding=embedding,
                conversation=conversation, pseudonymizer=pseudonymizer, style_guard=False, assistance=True,
            )
            messages = list(plan.job.messages)
            # The public history already includes the latest customer message.
            messages.pop()
            directive = (MESSENGER_STYLE_GUARD + "\n"
                         "Prepare a reply draft for the employee to review. Do not emit handoff tokens.")
            if suggestion.position > 1:
                directive += " Use a different wording from the earlier suggestions."
                for previous in suggestion.attempt.suggestions.filter(status=Status.READY):
                    messages.append(ChatMessage(role="assistant",
                        content=pseudonymizer.mask(previous.original_text), masked=True))
            messages.insert(0, ChatMessage(role="system", content=directive))
            remaining = time_left(suggestion)
            plan = replace(plan, job=replace(plan.job, messages=messages))
        if remaining <= 0:
            with tenant_atomic(context):
                current = load_suggestion(context, public_id)
                if current and current.status == Status.RUNNING:
                    finish(current, error=Error.TIMEOUT)
            return
        answer = run_turn_chat(plan, time_left=remaining)
        with tenant_atomic(context):
            current = load_suggestion(context, public_id)
            if current is None or current.status != Status.RUNNING:
                return
            safe_error = ProviderError(Error.GENERATION_FAILED)
            safe_answer = replace(answer,
                error=safe_error if answer.error else None,
                rounds=tuple(replace(r, error=safe_error if r.error else None)
                             for r in answer.rounds))
            text = record_turn(agent=agent, plan=plan, answer=safe_answer).replace(HANDOFF_TOKEN, "").strip()
            error = Error.TIMEOUT if time_left(current) <= 0 else ""
            try:
                reply_context(requester_context(context, current), conversation.pk)
            except APIException:
                error = Error.PERMISSION_DENIED
            if not error and (answer.error or not text):
                error = Error.GENERATION_FAILED
            finish(current, text=text, error=error)
    except Exception as exception:
        # Never persist or log provider payloads/secrets, including unexpected errors.
        with tenant_atomic(context):
            current = load_suggestion(context, public_id)
            if current and current.status == Status.RUNNING:
                error = Error.TIMEOUT if time_left(current) <= 0 else (
                    Error.PROVIDER_UNAVAILABLE if isinstance(exception, ProviderError)
                    else Error.GENERATION_FAILED)
                finish(current, error=error)
