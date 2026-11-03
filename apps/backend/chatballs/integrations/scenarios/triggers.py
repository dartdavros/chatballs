"""Launch configuration, independent of the future event/schedule workers."""

from datetime import date, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from chatballs.integrations.scenarios.definition import TRIGGER_KINDS, Issue, valid_id

TRIGGER_FIELDS = {
    "staff": set(), "ai": {"agents"}, "api": set(), "scenario": set(),
    "chatballs": {"event"}, "service": {"event", "connection"},
    "schedule": {"timezone", "days", "date", "time", "misfire", "ambiguous", "nonexistent", "frequency", "dayOfMonth"},
}


def check_triggers(triggers, *, context, path, issues):
    if not isinstance(triggers, list) or len(triggers) > 100:
        issues.append(Issue(path, "structure"))
        return
    identifiers = set()
    for i, trigger in enumerate(triggers):
        at = f"{path}.{i}"
        if not isinstance(trigger, dict) or trigger.get("kind") not in TRIGGER_KINDS:
            issues.append(Issue(at, "trigger"))
            continue
        kind = trigger["kind"]
        identifier = trigger.get("id")
        if not valid_id(identifier) or identifier in identifiers:
            issues.append(Issue(f"{at}.id", "identifier"))
        identifiers.add(str(identifier))
        if set(trigger) - (TRIGGER_FIELDS[kind] | {"id", "kind"}):
            issues.append(Issue(at, "unknown"))
        if kind in {"service", "chatballs"}:
            connection = str(trigger.get("connection", ""))
            if (connection, trigger.get("event", "")) not in context.events:
                issues.append(Issue(f"{at}.event", "reference"))
        if kind == "schedule":
            _schedule(trigger, at, issues)
        if kind == "ai" and (not isinstance(trigger.get("agents", []), list) or any(type(agent) is not int or agent not in context.agents for agent in trigger.get("agents", []))):
            issues.append(Issue(f"{at}.agents", "reference"))


def _schedule(trigger, path, issues):
    try:
        ZoneInfo(trigger.get("timezone", ""))
        clock = time.fromisoformat(trigger.get("time", ""))
        if clock.tzinfo is not None:
            raise ValueError("time")
        frequency = trigger.get("frequency", "days")
        if trigger.get("date"):
            date.fromisoformat(trigger["date"])
        elif frequency == "monthly":
            day = trigger.get("dayOfMonth")
            if day != "last" and (type(day) is not int or not 1 <= day <= 28):
                raise ValueError("dayOfMonth")
        elif frequency in {"daily", "weekdays"}:
            pass
        elif frequency != "days":
            raise ValueError("frequency")
        else:
            days = trigger.get("days")
            if not isinstance(days, list) or not days or any(type(d) is not int or not 0 <= d <= 6 for d in days):
                raise ValueError("days")
        if trigger.get("date") and trigger.get("days"):
            raise ValueError("schedule")
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        issues.append(Issue(path, "schedule"))
    for key, choices in {"misfire": {"skip", "once"}, "ambiguous": {"first", "second"},
                         "nonexistent": {"skip", "next"}}.items():
        if trigger.get(key) not in choices:
            issues.append(Issue(f"{path}.{key}", "policy"))


def check_access(access, triggers, issues, context):
    fields = {"staff", "groups", "aiMode", "delegated", "scope", "confirm"}
    if not isinstance(access, dict) or set(access) != fields:
        issues.append(Issue("access", "policy"))
        return
    if access["aiMode"] not in {"off", "confirm", "autonomous"} or access["scope"] not in {"conversation", "contact", "organization"}:
        issues.append(Issue("access", "policy"))
    if access["confirm"] not in {"effects", "always"} or not isinstance(access["delegated"], bool):
        issues.append(Issue("access", "policy"))
    for key in ("staff", "groups"):
        allowed = context.staff if key == "staff" else context.groups
        if not isinstance(access[key], list) or any(type(v) is not int or v not in allowed for v in access[key]):
            issues.append(Issue(f"access.{key}", "reference"))
    auto = {"chatballs", "service", "schedule", "api", "scenario"}
    if isinstance(triggers, list) and any(isinstance(t, dict) and t.get("kind") in auto for t in triggers):
        if access["delegated"] is not True:
            issues.append(Issue("access.delegated", "delegation"))
