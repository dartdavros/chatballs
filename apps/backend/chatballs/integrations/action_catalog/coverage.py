"""Complete app/platform/socket inventory, independent of domain prefixes."""

import json
from pathlib import Path

from chatballs.integrations.action_catalog.http_coverage import (
    framework_entries,
    mounted_http_entries,
)
from chatballs.integrations.action_catalog.protocol_coverage import mounted_protocol_entries
from chatballs.integrations.action_catalog.registry import native_actions

STAFF = "api/v1/organizations/<uuid:organization_public_id>/"
CLASSIFICATIONS = frozenset({"product", "credential_protocol", "transport", "health", "protocol"})


def entry_key(row):
    return row.get("surface", "app"), row["route"], row["method"], row["handler"]


def inventory():
    rows = [row for path in sorted(Path(__file__).parent.glob("*_inventory.json"))
        for row in json.loads(path.read_text(encoding="utf-8"))]
    return rows + list(framework_entries(rows))


def _route(route):
    return route if route.startswith(("api/", "ws/", "chat-widget.js")) else STAFF + route


def mounted_entries():
    return mounted_http_entries() | {("app", *entry) for entry in mounted_protocol_entries()}


def problems(*, action_prefix=None):
    rows = inventory()
    expected = {entry_key(row): row for row in rows}
    actual = mounted_entries()
    issues = [f"Unclassified API: {entry}" for entry in actual - set(expected)]
    issues += [f"Stale API: {entry}" for entry in set(expected) - actual]
    if len(expected) != len(rows):
        issues.append("Duplicate inventory entries")
    registered = {action.key: action for action in native_actions(authority=None)}
    root = Path(__file__).resolve().parents[5]
    evidence_paths = {path for row in rows for path in row.get("evidence", [])}
    missing_paths = {path for path in evidence_paths if not (root / path).is_file()}
    for entry, row in expected.items():
        if row.get("classification") not in CLASSIFICATIONS:
            issues.append(f"Missing classification: {entry}")
        if not row.get("evidence") or any(path in missing_paths for path in row["evidence"]):
            issues.append(f"Missing code evidence: {entry}")
        key = row.get("action")
        if key is None:
            if not row.get("reason") or row.get("classification") == "product":
                issues.append(f"Unexplained exclusion: {entry}")
            continue
        if row.get("classification") != "product":
            issues.append(f"Product action classified as protocol: {entry}")
        if action_prefix and not key.startswith(action_prefix):
            continue
        action = registered.get(key)
        if action is None:
            issues.append(f"Unregistered product action: {key}")
            continue
        if row.get("authority") != action.authority:
            issues.append(f"Authority mismatch: {key}: {entry}")
        references = {(e.surface, _route(e.route), e.method, e.handler) for e in action.entries}
        if entry not in references:
            issues.append(f"Action has no exact API reference: {key}: {entry}")
    for key, action in registered.items():
        if not action.entries:
            issues.append(f"Action has no product API: {key}")
        for e in action.entries:
            entry = (e.surface, _route(e.route), e.method, e.handler)
            if entry not in expected or expected[entry].get("action") != key:
                issues.append(f"Unmapped descriptor API: {key}: {entry}")
    return issues
