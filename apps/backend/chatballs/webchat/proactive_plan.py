"""Use the existing orchestrator, with a trusted task instead of a customer line."""

import json
from dataclasses import replace

from chatballs.ai.models import AnswerLanguage
from chatballs.ai.provider.base import ChatMessage
from chatballs.ai.runtime import ANSWER_IN_FIXED_LANGUAGE, LANGUAGE_LABELS
from chatballs.ai.turn import plan_chat
from chatballs.i18n import DEFAULT_LANGUAGE, customer_language
from chatballs.integrations.execution.budgets import root_of
from chatballs.integrations.execution.permissions import ExecutionDenied


def instruction(run, step):
    frame = run.progress.filter(path=step.path).first()
    if frame is None:
        raise ExecutionDenied("permission")
    binding = frame.definition.get("block", {}).get("inputs", {}).get("instruction", {})
    value = binding.get("value")
    if (set(binding) != {"source", "value"} or binding["source"] != "constant"
            or not isinstance(value, str) or not value.strip()
            or step.definition["arguments"].get("instruction") != value):
        raise ExecutionDenied("permission")
    return value


def first_plan(turn, run, claim):
    payload = root_of(run).definition["event"]["data"]
    plan = plan_chat(agent=turn.agent, message=turn.query, history=[],
        conversation=turn.conversation, pseudonymizer=turn.pseudonymizer,
        client_context=[("Site event data", json.dumps(payload, ensure_ascii=False, allow_nan=False))],
        action_turn_id=f"site:{claim.pk}", site_event_launch_id=claim.pk)
    # plan_chat provides knowledge, grants, skills and normal tools. Only its
    # last input changes role: no customer utterance is persisted or fabricated.
    messages = list(plan.job.messages)
    if not messages or messages[-1].role != "user":
        raise ExecutionDenied("arguments")
    messages[-1] = ChatMessage(role="system", content=turn.pseudonymizer.mask(
        "Trusted scenario task for the first reply:\n" + turn.query), masked=True)
    if turn.agent.answer_language in {AnswerLanguage.MIRROR, AnswerLanguage.ORGANIZATION}:
        messages.append(ChatMessage(role="system", content=ANSWER_IN_FIXED_LANGUAGE.format(
            language=LANGUAGE_LABELS[customer_language(turn.agent.organization) or DEFAULT_LANGUAGE])))
    return replace(plan, job=replace(plan.job, messages=messages))
