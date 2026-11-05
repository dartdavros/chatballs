"""Administrative per-field decisions never authorize a stale overwrite."""

import hashlib
import json

from django.utils import timezone

from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.events import journal, schedule
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.scenarios.synchronization_access import active_pair, actor_for
from chatballs.integrations.scenarios.synchronization_runtime import lock
from chatballs.tenancy.database import tenant_atomic


def digest(row):
    data = row.definition
    return hashlib.sha256(json.dumps({"id": row.pk, "generation": row.generation,
        "linkRevision": row.link.revision, "settingsRevision": row.settings.revision,
        "observed": data.get("observed"), "conflicts": data.get("conflicts")}, sort_keys=True).encode()).hexdigest()


def payload(tenant, run):
    if run.state != "decision" or run.data_cleared_at or run.definition.get("kind") != "synchronization":
        return None
    actor = current_actor(tenant)
    if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        return None
    row = lock(tenant, run.definition["exchange"]["checkpoint"])
    from chatballs.ai.diagnostic_redaction import integration_secrets
    from chatballs.i18n import t
    from chatballs.integrations.adapters.registry import default_registry
    from chatballs.integrations.execution.payloads import clean_value
    from chatballs.integrations.scenarios.catalog import CONTEXT
    from chatballs.integrations.scenarios.types import at_path
    from chatballs.integrations.service_connections.binding import resolve as resolve_connection
    from chatballs.integrations.service_connections.payloads import field_payload
    _, adapter, _ = resolve_connection(row.link.integration, default_registry())
    entity = next(e for e in adapter.entities if e.key == row.link.external_kind)
    data = row.definition
    native_left = data["pair"]["left"]["connection"] == "chatballs"
    native_schema = CONTEXT.field(row.link.internal_kind)
    secrets = integration_secrets([row.link.integration])
    items = []
    for item in data["conflicts"]:
        local_field = item["leftField"] if native_left else item["rightField"]
        remote_field = item["rightField"] if native_left else item["leftField"]
        local_spec, remote_spec = at_path(native_schema, local_field), at_path(entity.fields, remote_field)
        left_spec, right_spec = (local_spec, remote_spec) if native_left else (remote_spec, local_spec)
        items.append({"id": item["id"], "field": t(local_spec.title_key) if local_spec and local_spec.title_key else t("runs.field"),
            "left": clean_value(left_spec, item["left"], secrets), "right": clean_value(right_spec, item["right"], secrets),
            "leftSchema": field_payload("", left_spec) if left_spec else None, "rightSchema": field_payload("", right_spec) if right_spec else None,
            "leftAt": item["leftAt"], "rightAt": item["rightAt"]})
    return {"digest": digest(row), "leftTitle": "Chatballs" if native_left else row.link.integration.name,
        "rightTitle": row.link.integration.name if native_left else "Chatballs", "items": items}


def resolve(tenant, public_id, *, expected_digest, choices):
    with tenant_atomic(tenant):
        actor = current_actor(tenant)
        if actor.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")
        from chatballs.integrations.execution.budgets import lock_run
        run = lock_run(tenant, public_id)
        if run.state != "decision" or run.definition.get("kind") != "synchronization":
            raise ExecutionDenied("state_changed")
        row = lock(tenant, run.definition["exchange"]["checkpoint"])
        actor_for(tenant, row.settings)
        active_pair(row.settings, row.pair_id)
        if (row.run_id != run.pk or digest(row) != expected_digest
                or row.link.revision != run.definition["exchange"]["link"]["revision"] or row.settings.revision != run.revision):
            raise ExecutionDenied("state_changed")
        data = row.definition
        required = {item["id"] for item in data["conflicts"]}
        if not isinstance(choices, dict) or set(choices) != required or any(value not in {"left", "right"} for value in choices.values()):
            raise ExecutionDenied("arguments")
        data["resolution"] = {"choices": choices, "versions": {side: data["observed"][side]["version"] for side in ("left", "right")},
            "linkRevision": row.link.revision}
        row.definition, row.state = data, "running"
        row.save(update_fields=["content", "state"])
        run.steps.filter(operation_key="synchronization.plan", state="decision").update(state="queued", due_at=timezone.now(), lease_until=None)
        run.progress.filter(path="steps/plan").update(state="queued")
        run.state = "queued"
        run.save(update_fields=["state"])
        journal(run, "changed")
        record_audit_event(action="integrations.synchronization_resolved", actor=actor.actor_user, organization=actor.organization,
            object_type="ScenarioRun", object_id=str(run.public_id), payload={"fields": sorted(required)})
        schedule(tenant, run)
        return run
