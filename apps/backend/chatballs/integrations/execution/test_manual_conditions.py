"""A future form value is unknown, not false; known context guards fail closed."""

from copy import deepcopy

from django.test import SimpleTestCase

from chatballs.integrations.execution.manual_conditions import require_known_conditions
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios.definition import empty_definition


class ManualConditionTests(SimpleTestCase):
    known_false = {"kind": "context_present", "path": "contact", "present": True}
    known_true = {"kind": "context_present", "path": "contact", "present": False}
    future = {"left": {"source": "parameter", "name": "choice"}, "op": "eq",
              "right": {"source": "constant", "value": "yes"}}

    def document(self, mode, *conditions):
        result = empty_definition()
        result["conditions"] = {"mode": mode, "items": deepcopy(list(conditions))}
        return result

    def test_missing_future_parameters_do_not_hide_an_action(self):
        for mode in ("all", "any"):
            require_known_conditions(self.document(mode, self.future), None)
        require_known_conditions(self.document("all", self.known_true, self.future), None)
        require_known_conditions(self.document("any", self.known_false, self.future), None)

    def test_known_false_all_and_fully_false_any_are_unavailable(self):
        for document in (self.document("all", self.known_false, self.future),
                         self.document("any", self.known_false)):
            with self.assertRaisesMessage(ExecutionDenied, "conditions_not_met"):
                require_known_conditions(document, None)

    def test_provided_values_are_checked_again_before_launch(self):
        document = self.document("all", self.future)
        require_known_conditions(document, None, parameters={"choice": "yes"})
        with self.assertRaisesMessage(ExecutionDenied, "conditions_not_met"):
            require_known_conditions(document, None, parameters={"choice": "no"})

    def test_unsupported_context_is_denied_even_when_another_any_guard_passes(self):
        deferred = {"kind": "context_present", "path": "conversation.topic", "present": False}
        with self.assertRaisesMessage(ExecutionDenied, "conditions_unavailable"):
            require_known_conditions(self.document("any", self.known_true, deferred), None)

    def test_nested_future_binding_is_unknown_and_constant_objects_stay_literal(self):
        condition = {"left": {"nested": self.future["left"]}, "op": "eq",
                     "right": {"source": "constant", "value": {"nested": "yes"}}}
        require_known_conditions(self.document("all", condition), None)
        literal = {"source": "constant", "value": {"source": "parameter", "name": "not-a-binding"}}
        require_known_conditions(self.document("all", {"left": literal, "op": "eq", "right": literal}), None)
