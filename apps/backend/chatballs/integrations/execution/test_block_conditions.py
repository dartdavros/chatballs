"""Branch conditions accept lexical values while deferred sources stay blocked."""

from django.test import SimpleTestCase

from chatballs.integrations.execution.conditions import evaluate_conditions
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.scenarios.values import RunValues


class BlockConditionTests(SimpleTestCase):
    def test_condition_group_uses_recorded_previous_result(self):
        group = {"conditions": {"mode": "all", "items": [
            {"left": {"source": "step", "step": "read", "path": "value"}, "op": "eq",
             "right": {"source": "constant", "value": "ready"}}]}}
        self.assertTrue(evaluate_conditions(group, None, {}, values=RunValues(steps={"read": {"value": "ready"}})))
        self.assertFalse(evaluate_conditions(group, None, {}, values=RunValues(steps={"read": {"value": "other"}})))

    def test_unavailable_source_inside_an_unselected_branch_is_not_false(self):
        document = {"conditions": {"mode": "all", "items": []}, "steps": [
            {"kind": "if", "id": "choice", "condition": {"mode": "any", "items": [
                {"kind": "context_present", "path": "conversation.topic", "present": False}]},
             "then": [], "else": []}]}
        with self.assertRaisesRegex(ExecutionDenied, "conditions_unavailable"):
            require_supported_sources(document)

    def test_missing_required_reference_cannot_become_false(self):
        group = {"conditions": {"mode": "all", "items": [
            {"left": {"source": "step", "step": "missing", "path": "value"}, "op": "empty"}]}}
        with self.assertRaisesRegex(ExecutionDenied, "arguments"):
            evaluate_conditions(group, None, {}, values=RunValues())
