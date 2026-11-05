"""Freeze reachable definitions and operation contracts before the first effect."""

import hashlib
from copy import deepcopy

from chatballs.integrations.execution.actions import connection_key, resolve_action
from chatballs.integrations.execution.budgets import MAX_SNAPSHOT, size
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import child_lists


def signature(operation):
    return hashlib.sha256(repr((operation.key, operation.input, operation.output,
        operation.effect, operation.retry, operation.mode, operation.permission_scope)).encode()).hexdigest()


def walk(steps, depth=0):
    if depth >= 16:
        raise ExecutionDenied("budget_depth")
    for block in steps:
        yield block
        for _, children in child_lists(block):
            yield from walk(children, depth + 1)


def freeze(tenant, document, *, scenario_id, registry=None):
    graph, contracts, heights, events = {}, {}, {}, {}

    def visit(identity, data, chain):
        if identity in chain:
            raise ExecutionDenied("recursion")
        if len(chain) >= 16:
            raise ExecutionDenied("budget_depth")
        if identity in heights:
            if len(chain) + heights[identity] > 16:
                raise ExecutionDenied("budget_depth")
            return heights[identity]
        height = 1
        require_supported_sources(data)
        blocks = list(walk(data["steps"]))
        if len(blocks) > 1000:
            raise ExecutionDenied("budget_execution")
        for block in blocks:
            if block["kind"] == "action":
                resolved = resolve_action(tenant.organization_id, block.get("connection"), block["target"], registry=registry)
                integration, _, adapter, _, operation = resolved
                key = f"{connection_key(integration)}:{block['target']}"
                from chatballs.integrations.execution.contract_schemas import write_spec
                contracts[key] = {"adapter": adapter.key, "version": adapter.contract_version,
                                  "signature": signature(operation), "input": write_spec(operation.input),
                                  "output": write_spec(operation.output), "title_key": operation.title_key}
            if block["kind"] == "wait" and block["mode"] == "event" and str(block.get("connection", "")).isdecimal():
                from chatballs.integrations.execution.contract_schemas import write_spec
                from chatballs.integrations.models import Integration
                from chatballs.integrations.service_connections.binding import resolve
                connection = Integration.objects.get(pk=block["connection"], organization_id=tenant.organization_id)
                _, adapter, _ = resolve(connection, registry)
                event = next((e for e in adapter.events if e.key == block["event"]), None)
                if event is None or not connection.is_active or connection.status != "OK":
                    raise ExecutionDenied("connection_paused")
                events[f"{connection.pk}:{event.key}"] = write_spec(event.payload)
            elif block["kind"] == "wait" and block["mode"] == "event":
                from chatballs.integrations.execution.contract_schemas import write_spec
                from chatballs.integrations.scenarios.native_events import NATIVE_EVENTS
                payload = next((schema for key, _title, schema in NATIVE_EVENTS if key == block["event"]), None)
                if payload is None:
                    raise ExecutionDenied("event_unavailable")
                events[f":{block['event']}"] = write_spec(payload)
            if block["kind"] == "call":
                key = str(block["scenario"])
                # Check cycles even if a shared node has already been collected.
                child = ScenarioDefinition.objects.filter(public_id=key, organization_id=tenant.organization_id).first()
                if child is None or not child.enabled:
                    raise ExecutionDenied("scenario_disabled")
                if key in chain or key == identity:
                    raise ExecutionDenied("recursion")
                if key not in graph:
                    graph[key] = {"id": child.pk, "revision": child.revision, "name": child.name,
                                  "document": deepcopy(child.definition)}
                height = max(height, 1 + visit(key, graph[key]["document"], chain + [identity]))
                if size(graph) > MAX_SNAPSHOT:
                    raise ExecutionDenied("budget_volume")
        heights[identity] = height
        return height
    visit(str(scenario_id), document, [])
    result = {"graph": graph, "contracts": contracts, "events": events}
    if size({"document": document, **result}) > MAX_SNAPSHOT:
        raise ExecutionDenied("budget_volume")
    return result


def check_contract(run, block, operation, adapter):
    saved = run.definition["contracts"].get(f"{block['connection']}:{block['target']}")
    if saved is None or {key: saved[key] for key in ("adapter", "version", "signature")} != {
            "adapter": adapter.key, "version": adapter.contract_version, "signature": signature(operation)}:
        raise ExecutionDenied("version_incompatible")
