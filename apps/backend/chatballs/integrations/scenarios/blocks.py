"""Structural and lexical scope validation for every composite block."""

from __future__ import annotations

from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.scenarios.bindings import binding_type, check_binding, transformed_type
from chatballs.integrations.scenarios.conditions import check_conditions
from chatballs.integrations.scenarios.definition import BLOCK_KINDS, Issue, child_lists, valid_id
from chatballs.integrations.scenarios.native_references import check_native_references

FIELDS = {
    "action": {"target", "connection", "inputs", "onError"},
    "if": {"condition", "then", "else"},
    "foreach": {"list", "body", "concurrency", "onError"},
    "parallel": {"branches", "onError"},
    "call": {"scenario", "inputs"},
    "wait": {"mode", "duration", "until", "event", "connection", "condition", "timeout", "onTimeout", "day", "date", "time", "timezone", "approver", "message"},
    "try": {"body", "catch", "after"},
}


class BlockValidator:
    def __init__(self, *, context, registry, issues):
        self.context = context
        self.registry = registry
        self.issues = issues
        self.ids = set()

    def issue(self, path, code):
        self.issues.append(Issue(path, code))

    def binding(self, value, target, scope, path):
        check_binding(value, target, scope=scope, context=self.context, registry=self.registry,
                      path=path, issues=self.issues)

    def conditions(self, group, scope, path):
        check_conditions(group, scope=scope, context=self.context, registry=self.registry,
                         path=path, issues=self.issues)

    def steps(self, steps, scope, path="steps", depth=0):
        if not isinstance(steps, list) or depth > 16 or len(self.ids) + len(steps) > 1000:
            self.issue(path, "structure")
            return
        for i, step in enumerate(steps):
            at = f"{path}.{i}"
            if not isinstance(step, dict) or step.get("kind") not in BLOCK_KINDS:
                self.issue(at, "block")
                continue
            kind = step["kind"]
            sid = step.get("id")
            if not valid_id(sid) or sid in self.ids:
                self.issue(f"{at}.id", "identifier")
                continue
            self.ids.add(sid)
            if "name" in step and (not isinstance(step["name"], str) or len(step["name"]) > 200):
                self.issue(f"{at}.name", "structure")
            if set(step) - (FIELDS[kind] | {"id", "kind", "name"}):
                self.issue(at, "unknown")
            if kind == "foreach":
                if type(step.get("concurrency", 1)) is not int or not 1 <= step.get("concurrency", 1) <= 5:
                    self.issue(f"{at}.concurrency", "policy")
                if step.get("onError", "continue") not in {"stop", "continue"}:
                    self.issue(f"{at}.onError", "policy")
            if kind == "parallel" and step.get("onError", "wait") not in {"wait", "stop", "continue"}:
                self.issue(f"{at}.onError", "policy")
            if kind == "try" and step.get("after", "continue") not in {"continue", "fail"}:
                self.issue(f"{at}.after", "policy")
            output = self._block(step, scope, at)
            expected_children = {"if": {"then", "else"}, "foreach": {"body"}, "try": {"body", "catch"}}
            for key in expected_children.get(kind, set()):
                if not isinstance(step.get(key), list):
                    self.issue(f"{at}.{key}", "structure")
            if kind == "parallel":
                branches = step.get("branches")
                if not isinstance(branches, list) or len(branches) < 2 or any(not isinstance(b, list) for b in branches):
                    self.issue(f"{at}.branches", "structure")
            for key, children in child_lists(step):
                nested = scope.fork()
                if kind == "foreach":
                    spec = binding_type(step.get("list", {}), scope, self.context)
                    if spec:
                        spec = transformed_type(step["list"], spec, self.registry)
                    if spec and spec.type == "array" and spec.items:
                        nested.items[sid] = spec.items
                if kind == "try" and key == "catch":
                    nested.errors.add(sid)
                self.steps(children, nested, f"{at}.{key}", depth + 1)
            if output:
                scope.steps[sid] = output
            scope.states.add(sid)

    def _block(self, step, scope, path):
        kind = step["kind"]
        if kind in {"action", "call"}:
            if kind == "action":
                pair = self.context.operations.get((str(step.get("connection", "")), step.get("target", "")))
            else:
                pair = self.context.scenarios.get(str(step.get("scenario", "")))
            if pair is None:
                self.issue(path, "reference")
                return None
            self.binding(step.get("inputs", {}), pair[0], scope, f"{path}.inputs")
            if kind == "action":
                check_native_references(step, self.context, path, self.issues)
            if kind == "action" and step.get("onError", "stop") not in {"stop", "continue"}:
                self.issue(f"{path}.onError", "policy")
            return pair[1]
        if kind == "if":
            self.conditions(step.get("condition"), scope, f"{path}.condition")
        if kind == "foreach":
            value = step.get("list", {})
            spec = binding_type(value, scope, self.context) if isinstance(value, dict) else None
            if spec:
                spec = transformed_type(value, spec, self.registry)
            if spec is None or spec.type != "array":
                self.issue(f"{path}.list", "type")
            else:
                self.binding(value, spec, scope, f"{path}.list")
        if kind == "wait":
            self._wait(step, scope, path)
        from chatballs.integrations.scenarios.result_schemas import block_output
        return block_output(step, self.context)

    def _wait(self, step, scope, path):
        mode = step.get("mode")
        if mode == "duration":
            value = step.get("duration")
            if type(value) is not int or value <= 0:
                self.issue(f"{path}.duration", "required")
        elif mode == "until":
            self.binding(step.get("until"), TypeSpec("datetime", required=True), scope, f"{path}.until")
        elif mode == "event":
            event = self.context.events.get((str(step.get("connection", "")), step.get("event", "")))
            if event is None:
                self.issue(f"{path}.event", "reference")
            nested = scope.fork()
            nested.event = event or TypeSpec("object")
            self.conditions(step.get("condition"), nested, f"{path}.condition")
        elif mode == "clock":
            from datetime import date, time
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            try:
                ZoneInfo(step.get("timezone", ""))
                time.fromisoformat(step.get("time", ""))
                if step.get("day") == "date":
                    date.fromisoformat(step.get("date", ""))
                elif step.get("day") not in {"next", "work"}:
                    raise ValueError("day")
            except (ValueError, TypeError, ZoneInfoNotFoundError):
                self.issue(path, "schedule")
        elif mode == "reply":
            pass
        elif mode == "confirmation":
            if "message" in step and (not isinstance(step["message"], str) or len(step["message"]) > 2000):
                self.issue(f"{path}.message", "type")
            approver = step.get("approver", "initiator")
            if approver != "initiator" and (not isinstance(approver, str) or not approver.isdecimal() or int(approver) not in self.context.staff):
                self.issue(f"{path}.approver", "reference")
        else:
            self.issue(f"{path}.mode", "required")
        if step.get("onTimeout", "continue") not in {"continue", "end"}:
            self.issue(f"{path}.onTimeout", "policy")
        if "timeout" in step and (type(step["timeout"]) is not int or step["timeout"] <= 0):
            self.issue(f"{path}.timeout", "type")
