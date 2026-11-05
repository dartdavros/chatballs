"""Private WEB rule and its deliberately small public projection."""

from uuid import UUID, uuid4

from chatballs.webchat.site_event_schema import NAME, normalize_schema, reject

EVENT_KEY = "webchat.site_event"


def normalize_rule(config, previous):
    if "siteEvent" not in config:
        return previous.get("siteEvent")
    raw = config["siteEvent"]
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) - {"id", "name", "schema", "invitation", "scenario", "active"}:
        reject()
    name, invitation = raw.get("name"), raw.get("invitation")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        reject()
    if not isinstance(invitation, str) or not 1 <= len(invitation.strip()) <= 1000:
        reject()
    if type(raw.get("active", False)) is not bool:
        reject()
    try:
        scenario = str(UUID(raw.get("scenario", "")))
    except (ValueError, TypeError, AttributeError):
        reject()
    old = previous.get("siteEvent") or {}
    # The browser cannot pick or reset the once-rule identity.
    return {"id": old.get("id") or uuid4().hex, "name": name,
        "schema": normalize_schema(raw.get("schema", [])), "invitation": invitation.strip(),
        "scenario": scenario, "active": raw.get("active", False)}


def configured_scenario(integration):
    from chatballs.integrations.scenario_state.definitions import ScenarioDefinition

    rule = integration.config.get("siteEvent")
    if not rule:
        return None
    scenario = ScenarioDefinition.objects.filter(organization_id=integration.organization_id,
        public_id=rule["scenario"]).first()
    if scenario is None:
        reject()
    document = scenario.definition
    if not any(t["kind"] == "chatballs" and t.get("event") == EVENT_KEY for t in document["triggers"]):
        reject()
    return scenario


def public_rule(integration):
    rule = integration.config.get("siteEvent")
    if not rule or not rule.get("active"):
        return None
    return {key: rule[key] for key in ("name", "schema", "invitation")}
