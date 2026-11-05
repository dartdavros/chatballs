"""Immutable exchange graphs use the existing interpreter and effect ledger."""

import hashlib

from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.composite_launch import snapshot
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.synchronization_access import actor_for, conversation_for


def action(identifier, connection, target, arguments):
    return {"id": identifier, "kind": "action", "connection": str(connection), "target": target,
        "inputs": {key: {"source": "constant", "value": value} for key, value in arguments.items()}}


def branch(identifier, flag, step):
    return {"id": identifier, "kind": "if", "condition": {"mode": "all", "items": [
        {"left": {"source": "step", "step": "plan", "path": flag}, "op": "eq",
         "right": {"source": "constant", "value": True}}]}, "then": [step], "else": []}


def planned_action(tenant, connection, target, key, *, registry=None):
    operation = resolve_action(tenant.organization_id, str(connection), target, registry=registry)[-1]
    step = action(key, connection, target, {})
    step["inputs"] = {name: {"source": "step", "step": "plan", "path": f"{key}Arguments.{name}"}
        for name, _ in operation.input.properties}
    return step


def cycle_steps(tenant, row, binding, *, registry=None):
    identifier = row.definition["link"]["external_id"]
    connection = row.link.integration_id
    steps = [action("read", connection, f"service:{binding.read_operation}", binding.read_arguments(identifier)),
             action("plan", "chatballs", "chatballs:synchronization.plan", {}),
             action("current", connection, f"service:{binding.read_operation}", binding.read_arguments(identifier)),
             action("validate", "chatballs", "chatballs:synchronization.validate", {})]
    if binding.update_operation:
        steps.append(branch("update_if_needed", "update", planned_action(tenant, connection,
            f"service:{binding.update_operation}", "update", registry=registry)))
    if binding.delete_operation:
        steps.append(branch("delete_if_needed", "delete", planned_action(tenant, connection,
            f"service:{binding.delete_operation}", "delete", registry=registry)))
    steps.append(branch("local_if_needed", "local", planned_action(tenant, "chatballs",
        "chatballs:synchronization.local", "local", registry=registry)))
    steps.extend([action("verify", connection, f"service:{binding.read_operation}", binding.read_arguments(identifier)),
                  action("checkpoint", "chatballs", "chatballs:synchronization.finish", {})])
    return steps


def launch(tenant, row, binding, *, registry=None, trigger_key=None):
    actor = actor_for(tenant, row.settings)
    conversation = conversation_for(actor, row.link)
    data = row.definition
    document = empty_definition()
    document["access"].update(scope="organization", delegated=True)
    document["steps"] = cycle_steps(tenant, row, binding, registry=registry)
    source = {"key": f"exchange:{row.pk}", "revision": row.settings.revision, "name": "",
        "updatedAt": row.settings.updated_at.isoformat(), "exchange": {
            "checkpoint": row.pk, "settings": row.settings_id, "generation": row.generation,
            "pair": data["pair"], "link": data["link"]}}
    key = hashlib.sha256((trigger_key or f"exchange:{row.pk}:{row.generation}").encode()).hexdigest()
    run = snapshot(actor, document, {}, conversation, scenario=None, source=source,
        dedup=key, registry=registry, preview=False, confirmation=None)
    run.structure = {**run.structure, "operationTitle": "runs.synchronization", "connection": row.link.integration.name}
    run.save(update_fields=["structure"])
    return run
