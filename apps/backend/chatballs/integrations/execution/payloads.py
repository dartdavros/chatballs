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
    payload["ai"] = bool(run.structure.get("agentName"))
    if payload["ai"]:
        payload["initiator"] = t("runs.ai_initiator", name=run.structure["agentName"])
    if not detail:
        from chatballs.integrations.execution.progress_payloads import extend_payload
        return extend_payload(run, payload, tenant=tenant, detail=False)
    from chatballs.integrations.execution.control import available_controls
    payload["controls"] = available_controls(tenant, run) if tenant else []
    if tenant and payload["ai"] and "approve" in payload["controls"]:
        from chatballs.integrations.execution.permissions import allowed_files
        payload["files"] = [{"id": str(file.public_id), "name": file.name} for file in allowed_files(tenant, run.conversation_id)]
    payload["reconcilePath"] = run.steps.filter(state="unknown").order_by("pk").values_list("path", flat=True).first()
    steps = []
    from chatballs.integrations.models import Integration
    all_secrets = integration_secrets(list(Integration.objects.filter(organization_id=run.organization_id)))
    for step in run.steps.select_related("integration", "integration__service_settings").order_by("id"):
        if not step.operation_key:
            continue
        adapter = default_registry().adapter(step.adapter_key)
        operation = adapter.operation(step.operation_key) if adapter and adapter.contract_version == step.adapter_version else None
        if step.adapter_key == "chatballs" and step.adapter_version == 1:
            from chatballs.integrations.execution.native import operation as native_operation
            operation = native_operation(step.operation_key)
        values = step.definition if not run.data_cleared_at else {}
        from chatballs.integrations.execution.contract_schemas import frozen_schemas
        input_spec, output_spec = frozen_schemas(run, step, operation) if run.content else (None, None)
        secrets = all_secrets
        item = {"path": step.path, "title": t(operation.title_key) if operation else t("runs.operation"),
            "state": "pending" if step.state == "waiting" else step.state, "stateLabel": t(f"runs.state_{'pending' if step.state == 'waiting' else step.state}"), "attempt": step.attempt,
            "error": t("runs.unknown_text") if step.state == "unknown" else error_message(step.error_code) if step.error_code else "",
            "inputSchema": field_payload("", input_spec) if input_spec else None,
            "outputSchema": field_payload("", output_spec) if output_spec else None,
            "arguments": clean_value(input_spec, values.get("arguments", {}), secrets) if input_spec else {},
            "result": clean_value(output_spec, values.get("result", {}), secrets) if output_spec else {}}
        if step.adapter_key == "chatballs" and step.operation_key.startswith("synchronization."):
            item.update(inputSchema=None, outputSchema=None, arguments={}, result={})
        if step.state == "approval":
            item["approvalDigest"] = invocation_digest(step, run)
            if run.definition.get("ai"):
                from chatballs.integrations.execution.ai_approval import active_editor
                editor = active_editor(step)
                item["deadline"] = run.definition["ai"]["approvalDeadline"]
                item["editing"] = bool(editor)
                if tenant and editor.get("membership") == tenant.membership_id:
                    item["editToken"] = editor["token"]
        item["connectionId"] = step.integration_id
        steps.append(item)
    payload["steps"] = steps
    if run.definition.get("kind") == "synchronization":
        from chatballs.integrations.scenarios.conflicts import payload as conflict_payload
        payload["conflict"] = conflict_payload(tenant, run) if tenant else None
    payload["journal"] = [{"id": row.pk, "label": t(f"runs.journal_{row.code}") if row.code in {
        "created", "claimed", "recovering", "retry_scheduled", "request_sent", "reconcile_sent", "approve", "cancel", "reconcile"
    } else t(f"runs.state_{row.code}") if row.code in {
        "completed", "failed", "cancelled", "unknown", "queued", "pending", "approval", "reconciling", "running"
    } else t("runs.journal_changed"), "createdAt": row.created_at.isoformat()}
        for row in run.journal.order_by("-id")[:100]]
    from chatballs.integrations.execution.progress_payloads import extend_payload
    return extend_payload(run, payload, tenant=tenant, detail=True)
