"""Localized run views. Stored journal entries never contain these values."""

import re

from chatballs.i18n import t
from chatballs.integrations.adapters.registry import default_registry
from chatballs.ai.diagnostic_redaction import integration_secrets
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.service_connections.payloads import field_payload

_SECRET_KEY = re.compile(r"token|secret|password|authorization|cookie|api.?key|credential", re.I)


def clean_value(spec, value, secrets, depth=0):
    if depth > 20 or spec and spec.secret:
        return {"redacted": True}
    if isinstance(value, dict):
        return {name: {"redacted": True} if _SECRET_KEY.search(name) else clean_value(
            spec.field(name) if spec else None, child, secrets, depth + 1) for name, child in value.items()}
    if isinstance(value, list):
        return [clean_value(spec.items if spec else None, child, secrets, depth + 1) for child in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, t("runs.hidden"))
    return value


def run_payload(run, *, detail=False, tenant=None):
    member = run.initiator
    payload = {"id": str(run.public_id), "number": run.pk,
        "name": run.structure.get("name") or t(run.structure.get("operationTitle") or "runs.operation"),
        "connection": run.structure.get("connection", ""), "state": run.state,
        "stateLabel": t(f"runs.state_{run.state}"), "initiator": member.user.full_name if member else "",
        "conversationId": run.conversation_id, "createdAt": run.created_at.isoformat(),
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        "cancelRequested": run.cancel_requested_at is not None, "dataCleared": run.data_cleared_at is not None,
        "revision": run.revision, "definitionUpdatedAt": run.structure.get("definitionUpdatedAt"),
        "progress": [{"title": t(run.structure.get("operationTitle") or "runs.operation"), "state": step.state,
                      "stateLabel": t(f"runs.state_{step.state}")} for step in run.steps.all()]}
    if not detail:
        return payload
    from chatballs.integrations.execution.control import available_controls
    payload["controls"] = available_controls(tenant, run) if tenant else []
    steps = []
    for step in run.steps.select_related("integration", "integration__service_settings").order_by("id"):
        adapter = default_registry().adapter(step.adapter_key)
        operation = adapter.operation(step.operation_key) if adapter and adapter.contract_version == step.adapter_version else None
        values = step.definition if not run.data_cleared_at else {}
        secrets = integration_secrets([step.integration]) if step.integration else []
        item = {"path": step.path, "title": t(operation.title_key) if operation else t("runs.operation"),
            "state": step.state, "stateLabel": t(f"runs.state_{step.state}"), "attempt": step.attempt,
            "error": t("runs.unknown_text") if step.state == "unknown" else error_message(step.error_code) if step.error_code else "",
            "inputSchema": field_payload("", operation.input) if operation else None,
            "outputSchema": field_payload("", operation.output) if operation else None,
            "arguments": clean_value(operation.input if operation else None, values.get("arguments", {}), secrets),
            "result": clean_value(operation.output if operation else None, values.get("result", {}), secrets)}
        if step.state == "approval":
            item["approvalDigest"] = invocation_digest(step, run)
        steps.append(item)
    payload["steps"] = steps
    payload["journal"] = [{"id": row.pk, "label": t(f"runs.journal_{row.code}") if row.code in {
        "created", "claimed", "recovering", "retry_scheduled", "request_sent", "reconcile_sent", "approve", "cancel", "reconcile"
    } else t(f"runs.state_{row.code}") if row.code in {
        "completed", "failed", "cancelled", "unknown", "queued", "pending", "approval", "reconciling", "running"
    } else t("runs.journal_changed"), "createdAt": row.created_at.isoformat()}
        for row in run.journal.order_by("-id")[:100]]
    return payload
