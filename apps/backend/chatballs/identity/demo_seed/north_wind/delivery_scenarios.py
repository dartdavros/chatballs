"""Seed ordinary Chatballs scenarios for the local carrier."""

from secrets import token_urlsafe

from chatballs.conversations.models import ConversationLabel
from chatballs.identity.demo_seed.north_wind.delivery_adapter import (
    ADAPTER,
    ENTITY,
    EVENT,
    ORDER_NUMBER,
    verify_delivery_service,
)
from chatballs.identity.demo_seed.north_wind.local_access import issue_local_read_token
from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.services import save_definition
from chatballs.integrations.service_connections.services import save_new_connection
from chatballs.tenancy.context import TenantContext


def create_delivery_queue(refs, names):
    organization_id = refs.recorder.dataset.organization_id
    label = ConversationLabel.objects.create(organization_id=organization_id, name=names["label"], color="#d97706")
    group = EmployeeGroup.objects.create(organization_id=organization_id, name=names["group"])
    EmployeeGroupMember.objects.create(
        organization_id=organization_id, group=group, employee=refs.memberships["igor"],
    )
    return group, label


def load_delivery_scenarios(refs, conversation, names, *, inbox=None):
    tenant = TenantContext.for_membership(refs.memberships["elena"])
    dataset = refs.recorder.dataset
    access_token = issue_local_read_token(dataset, customer="pavel")
    verify_delivery_service(access_token)
    connection = save_new_connection(
        context=tenant, adapter=ADAPTER, method=ADAPTER.auth_methods[0],
        name=names["connection"], settings={}, checked=True,
        credentials={"signature": token_urlsafe(32), "token": access_token},
    )
    EntityLink.objects.create(
        organization_id=tenant.organization_id, integration=connection,
        internal_kind="conversation", internal_id=conversation.pk, external_kind=ENTITY, external_id=str(ORDER_NUMBER),
    )
    group, label = inbox or create_delivery_queue(refs, names)
    reference = str(connection.pk)
    delayed = _definition(
        {"kind": "service", "id": "delay", "connection": reference, "event": EVENT},
        _service(reference, "shipment.status", {"source": "event", "path": "orderNumber"}),
        {
            "kind": "if", "id": "still-delayed",
            "condition": {"mode": "all", "items": [{
                "left": {"source": "step", "step": "shipment.status", "path": "status"},
                "op": "eq", "right": _constant("delayed"),
            }]},
            "then": [
                _native("priority", "conversations.priority.post", priority="HIGH"),
                _native("delivery-group", "conversations.group.post", group_id=group.pk),
                _native("control", "conversations.labels.post", labelIds=[label.pk]),
            ],
            "else": [],
        },
        delegated=True,
    )
    scheduled = _definition(
        {"kind": "schedule", "id": "daily", "frequency": "daily", "timezone": "Europe/Moscow",
         "time": "09:00", "ambiguous": "second", "nonexistent": "skip", "misfire": "once"},
        _service(reference, "shipment.status", _constant(ORDER_NUMBER)), scope="organization", delegated=True,
    )
    scheduled["results"]["properties"] = {"needsAttention": {"type": "boolean"}}
    scheduled["outputs"]["needsAttention"] = {"source": "step", "step": "shipment.status", "path": "needsAttention"}
    manual = _definition(
        {"kind": "staff", "id": "staff"}, _service(reference, "delivery.check", _constant(ORDER_NUMBER)),
    )
    manual["conditions"]["items"].append({
        "kind": "has_link", "entity": ENTITY, "connection": reference,
    })
    scenarios = {}
    for key, document in (("delay", delayed), ("schedule", scheduled), ("manual", manual)):
        scenario, issues = save_definition(tenant=tenant, name=names[key], document=document, enabled=True)
        if issues:
            raise RuntimeError(f"North Wind delivery scenario {key}: {issues}")
        scenarios[key] = scenario
    dataset.shop_state["deliveryAutomation"] = {
        "connectionId": connection.pk, "conversationId": conversation.pk, "groupId": group.pk,
        "scenarioIds": [scenario.pk for scenario in scenarios.values()],
        "scenarioRevisions": {str(scenario.pk): scenario.revision for scenario in scenarios.values()},
        "scheduleScenarioId": scenarios["schedule"].pk,
    }
    dataset.save(update_fields=["shop_state"])


def _definition(trigger, *steps, **access):
    document = empty_definition()
    document["triggers"] = [trigger]
    document["steps"] = list(steps)
    document["access"].update(access)
    return document


def _constant(value):
    return {"source": "constant", "value": value}


def _service(connection, method, number):
    return {"id": method, "kind": "action", "connection": connection, "target": f"service:{method}",
            "inputs": {"order_number": number}}


def _native(identifier, method, **inputs):
    return {"id": identifier, "kind": "action", "connection": "chatballs", "target": f"chatballs:{method}",
            "inputs": {"conversation_id": {"source": "context", "path": "conversation.id"},
                       **{key: _constant(value) for key, value in inputs.items()}}}
