"""Attach native first-reply scenarios to the shared storefront widget."""

from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.services import save_definition
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.site_event_config import EVENT_KEY, normalize_rule


def configure_site_scenario(refs, *, key, copy, event, task, schema):
    dataset = refs.recorder.dataset
    tenant = TenantContext.for_membership(refs.memberships["elena"])
    scenario = _first_reply(tenant, copy["name"], task)
    integration, widget = refs.integrations["web"], refs.widgets["web"]
    rule = normalize_rule({"siteEvent": {
        "name": event, "invitation": copy["invitation"], "scenario": str(scenario.public_id),
        "schema": schema, "active": True,
    }}, {})
    integration.config.setdefault("northWindSiteEvents", []).append(rule)
    integration.save(update_fields=["config"])
    dataset.shop_state[f"{key}Site"] = {
        "widgetKey": widget.public_key, "connectionId": integration.pk, "scenarioId": scenario.pk,
        "scenarioRevision": scenario.revision, "ruleId": rule["id"], "eventName": event,
    }


def _first_reply(tenant, name, task):
    document = empty_definition()
    document["triggers"] = [{"id": "selection", "kind": "chatballs", "event": EVENT_KEY}]
    document["access"].update(delegated=True, scope="conversation")
    document["steps"] = [{"id": "advise", "kind": "action", "connection": "chatballs",
                          "target": "chatballs:webchat.first_reply", "inputs": {
                              "instruction": {"source": "constant", "value": task},
                          }}]
    scenario, issues = save_definition(tenant=tenant, name=name, document=document, enabled=True)
    if scenario is None:
        raise RuntimeError(f"Invalid North Wind site scenario: {issues}")
    return scenario
