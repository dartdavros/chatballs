"""Save only sanitized request/response copies. No token-to-value maps are persisted."""

from dataclasses import asdict

from django.utils import timezone

from chatballs.ai.diagnostic_models import TurnDiagnostic
from chatballs.ai.diagnostic_storage import isolated_capture, prune_diagnostics
from chatballs.ai.runtime import HANDOFF_TOKEN


def request_payload(job):
    return {
        "model": job.model, "params": job.params,
        "messages": [asdict(message) for message in job.messages],
        "tools": [asdict(tool) for tool in job.tools or []],
    }


@isolated_capture
def start_diagnostic(message, plan):
    if plan.diagnostic_redactor is None:
        return
    payload = plan.diagnostic_redactor.clean({
        **plan.diagnostic_snapshot,
        "request": request_payload(plan.job), "fragmentIds": plan.fragment_ids,
    })
    payload["truncated"] = plan.diagnostic_redactor.truncated
    payload["state"] = "running"
    TurnDiagnostic.objects.update_or_create(message=message, defaults={"payload": payload})
    prune_diagnostics(message)


@isolated_capture
def finish_diagnostic(message, plan, answer):
    if plan.diagnostic_redactor is None:
        return
    rounds = [
        {"request": request_payload(job),
         "response": asdict(item.result) if item.result is not None else None,
         "error": str(item.error) if item.error is not None else "",
         "requestSent": item.request_sent,
         "latencyMs": item.latency_ms}
        for job, item in zip(answer.requests, answer.rounds, strict=True)
    ]
    if not answer.rounds:
        rounds = [{"request": request_payload(plan.job),
                   "response": asdict(answer.result) if answer.result else None,
                   "error": str(answer.error) if answer.error is not None else "",
                   "latencyMs": answer.latency_ms}]
    extra = plan.diagnostic_redactor.clean({
        "rounds": rounds,
        "toolCalls": [asdict(call) for call in answer.tool_calls],
        "handoff": bool(answer.error is not None or (
            answer.result is not None and HANDOFF_TOKEN in answer.result.text
        )),
    })
    diagnostic = TurnDiagnostic.objects.get(message=message)
    diagnostic.payload.update(extra)
    diagnostic.payload["state"] = "failed" if answer.error is not None else "completed"
    diagnostic.payload["finishedAt"] = timezone.now().isoformat()
    diagnostic.payload["truncated"] = plan.diagnostic_redactor.truncated
    diagnostic.save(update_fields=["payload"])


@isolated_capture
def record_planning_failure(message, agent, conversation, pseudonymizer, error):
    from chatballs.ai.diagnostic_snapshot import diagnostic_context

    _, redactor, snapshot = diagnostic_context(agent, conversation, pseudonymizer)
    payload = redactor.clean({**snapshot,
                             "error": str(error), "handoff": True})
    payload["state"] = "planning_failed"
    payload["truncated"] = redactor.truncated
    TurnDiagnostic.objects.update_or_create(message=message, defaults={"payload": payload})
    prune_diagnostics(message)
