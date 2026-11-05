"""Safe composite progress views; control authority is computed per path."""

from chatballs.i18n import t
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.wait_controls import can_decide, decision_digest

TITLES = {"if": "runs.block_if", "foreach": "runs.block_foreach", "parallel": "runs.block_parallel",
          "try": "runs.block_try", "call": "runs.block_call", "wait": "runs.block_wait"}


def extend_payload(run, payload, *, tenant, detail):
    if run.content and not run.definition.get("composite"):
        return payload
    frames = list(run.progress.exclude(kind="sequence").order_by("pk"))
    if not frames:
        return payload
    payload["progress"] = [{"title": (frame.definition["block"].get("name") if frame.content else "") or t(TITLES.get(frame.kind, "runs.operation")),
        "state": frame.state, "stateLabel": t(f"runs.state_{frame.state}")} for frame in frames]
    if not detail:
        return payload
    from chatballs.ai.diagnostic_redaction import integration_secrets
    from chatballs.integrations.execution.payloads import clean_value
    from chatballs.integrations.execution.result_payloads import (
        display_errors,
        label_schema,
        schema_and_names,
    )
    from chatballs.integrations.models import Integration
    secrets = integration_secrets(list(Integration.objects.filter(organization_id=run.organization_id)))
    items = {step["path"]: step for step in payload["steps"]}
    waits = {row.path: row for row in run.waits.all()}
    result = []
    for frame in frames:
        block = frame.definition["block"] if frame.content else {}
        item = items.pop(frame.path, None) or {"path": frame.path, "title": block.get("name") or t(TITLES.get(frame.kind, "runs.operation")),
            "state": frame.state, "stateLabel": t(f"runs.state_{frame.state}"), "attempt": 0,
            "error": error_message(frame.error_code) if frame.error_code else "",
            "inputSchema": None, "outputSchema": None, "arguments": {}, "result": {}}
        # Stable path is transported for actions, never printed as a technical label.
        item["depth"] = max(0, frame.path.count("/") - 1)
        item["scope"] = [{"kind": parts[i], "number": int(parts[i + 1]) + 1}
                         for parts in [frame.path.split("/")] for i in range(len(parts) - 1)
                         if parts[i] in {"iteration", "branch"} and parts[i + 1].isdecimal()]
        if frame.content and frame.kind != "action":
            spec, names = schema_and_names(run, block)
            if spec:
                item["outputSchema"] = label_schema(spec, names)
                item["result"] = display_errors(clean_value(spec, frame.definition.get("result", {}), secrets), block)
        row = waits.get(frame.path)
        if row:
            item["deadline"] = row.deadline.isoformat() if row.deadline else None
            if row.kind == "confirmation" and row.state == "pending":
                item["prompt"] = clean_value(None, block.get("message", ""), secrets)
                from chatballs.integrations.execution.launch_views import parameter_schema
                from chatballs.integrations.scenarios.types import read_type
                item["inputSchema"] = parameter_schema(run.definition["document"]["parameters"])
                item["arguments"] = clean_value(read_type(run.definition["document"]["parameters"]),
                                                run.definition["parameters"], secrets)
                item["state"] = "approval"
                item["stateLabel"] = t("runs.state_approval")
                if tenant:
                    try:
                        can_decide(tenant, row)
                        item["decision"] = {"generation": str(row.generation), "digest": decision_digest(row)}
                    except ExecutionDenied:
                        pass
        result.append(item)
    payload["steps"] = result + list(items.values())
    return payload
