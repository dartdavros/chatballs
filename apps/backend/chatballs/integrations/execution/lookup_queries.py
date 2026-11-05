"""Metadata reads retain visibility and frozen approval-contract checks."""

from chatballs.integrations.execution.actions import resolve_action, step_target
from chatballs.integrations.execution.ai_policy import approver
from chatballs.integrations.execution.journal_queries import journal_rows
from chatballs.integrations.execution.metadata import lookup_keys, metadata_action
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.snapshots import check_contract
from chatballs.integrations.service_connections.binding import load_lookup
from chatballs.tenancy.database import tenant_atomic


def lookup(tenant, integration, key):
    items = load_lookup(tenant=tenant, integration=integration, key=key)
    return {"items": [{"value": item.value, "label": item.label} for item in items]}


def manual(tenant, data):
    connection_id, conversation_id = int(data["connection"]), int(data["conversation"])
    with tenant_atomic(tenant):
        integration, _row, _adapter, _method, operation = metadata_action(tenant,
            connection_id=connection_id, operation_key=data.get("operation", ""), conversation_id=conversation_id,
            scenario_id=data.get("scenario"))
        if data.get("lookup") not in lookup_keys(operation.input):
            raise ExecutionDenied("permission")
    return lookup(tenant, integration, data["lookup"])


def approval(tenant, public_id, data):
    with tenant_atomic(tenant):
        run = journal_rows(tenant).get(public_id=public_id)
        approver(tenant, run)
        step = run.steps.get(path=data.get("path"))
        target = step_target(step)
        integration, _, adapter, _, operation = resolve_action(run.organization_id, target["connection"],
            target["target"], expected=(step.adapter_key, step.adapter_version))
        check_contract(run, target, operation, adapter)
        key = data.get("lookup")
        if key not in lookup_keys(operation.input):
            raise ExecutionDenied("permission")
    return lookup(tenant, integration, key)
