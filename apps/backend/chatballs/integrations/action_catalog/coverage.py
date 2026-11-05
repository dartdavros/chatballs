"""Product API coverage is checked against real mounted methods, never filenames."""

import json
from pathlib import Path

from django.urls import URLResolver, get_resolver

from chatballs.integrations.action_catalog.protocol_coverage import mounted_protocol_entries
from chatballs.integrations.action_catalog.registry import native_actions

STAFF = "api/v1/organizations/<uuid:organization_public_id>/"
ROOTS = tuple(STAFF + domain + "/" for domain in ("conversations", "calls", "notifications", "ratings")) + (
    "api/v1/calls/", "api/v1/ratings/", "api/v1/webchat/", STAFF + "company/",
    STAFF + "employees/",
    STAFF + "ai/", STAFF + "agents/", STAFF + "skills/", STAFF + "support/portals/", "api/v1/help/",
    "api/v1/ai/files/",
    STAFF + "integrations/",
)
METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
# These mounted API owners share the integrations prefix with scenario/runtime
# APIs, which are inventoried as their own product domain.
API_MODULES = frozenset({"chatballs.integrations.service_connections.views",
    "chatballs.integrations.service_connections.oauth_views", "chatballs.integrations.views",
    "chatballs.integrations.scenarios.views", "chatballs.integrations.scenarios.catalog_views",
    "chatballs.integrations.address_validation", "chatballs.webchat.asset_views"})


def inventory():
    return [row for name in ("api_inventory.json", "transport_inventory.json", "protocol_inventory.json",
                            "organization_inventory.json", "content_inventory.json", "agent_inventory.json", "skill_inventory.json", "portal_inventory.json", "service_inventory.json", "connection_inventory.json", "scenario_inventory.json")
        for row in json.loads(Path(__file__).with_name(name).read_text(encoding="utf-8"))]


def _route(route):
    return route if route.startswith(("api/", "ws/")) else STAFF + route


def mounted_entries():
    def walk(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                yield from walk(pattern.url_patterns, route)
            else:
                view = getattr(pattern.callback, "cls", None)
                if not route.startswith(ROOTS) and getattr(view, "__module__", "") not in API_MODULES:
                    continue
                if view is None:
                    yield route, "UNKNOWN", ""
                    continue
                handler = f"{view.__module__}.{view.__name__}"
                for method in sorted(METHODS):
                    if hasattr(view, method.lower()):
                        yield route, method, handler
    return set(walk(get_resolver("chatballs_backend.urls_app").url_patterns)) | mounted_protocol_entries()


def problems(*, action_prefix=None):
    expected = {(r["route"], r["method"], r["handler"]): r for r in inventory()}
    actual = mounted_entries()
    issues = [f"Unclassified API: {entry}" for entry in actual - set(expected)]
    issues += [f"Stale API: {entry}" for entry in set(expected) - actual]
    registered = {action.key: action for action in native_actions()}
    for entry, row in expected.items():
        key = row["action"]
        if key is None:
            if not row["reason"]:
                issues.append(f"Unexplained exclusion: {entry}")
            continue
        if action_prefix and not key.startswith(action_prefix):
            continue
        action = registered.get(key)
        if action is None:
            issues.append(f"Unregistered product action: {key}")
            continue
        references = {(_route(e.route),
            e.method, e.handler) for e in action.entries}
        if entry not in references:
            issues.append(f"Action has no exact API reference: {key}: {entry}")
    for key, action in registered.items():
        if not action.entries:
            issues.append(f"Action has no product API: {key}")
        for e in action.entries:
            entry = (_route(e.route), e.method, e.handler)
            if entry not in expected or expected[entry]["action"] != key:
                issues.append(f"Unmapped descriptor API: {key}: {entry}")
    return issues
