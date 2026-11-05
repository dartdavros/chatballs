"""A durable domain refusal is neither successful output nor an unknown effect."""

from dataclasses import replace
from types import SimpleNamespace

from django.test import SimpleTestCase

from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.native import _result
from chatballs.integrations.execution.native_results import restored
from chatballs.integrations.execution.permissions import ExecutionDenied


class NativeFailedResultTests(SimpleTestCase):
    def test_one_time_password_display_cannot_be_requested_or_bound_by_a_step(self):
        create = native_action("employees.post").operation
        reset = native_action("employees.reset_password").operation
        self.assertTrue(validate_value(create.input, {"email": "test@example.test", "fullName": "Test",
            "positionTitle": "Support", "passwordMode": "show"}))
        self.assertTrue(validate_value(reset.input, {"user_id": 1, "mode": "show"}))
        self.assertIsNone(create.output.field("password"))
        self.assertIsNone(reset.output.field("password"))

    def test_refusal_must_have_only_a_known_safe_error(self):
        action = native_action("employees.block")
        result = OperationResult(ResultState.FAILED, error_code="permission")
        self.assertEqual(_result(action, result), result)
        for invalid in (replace(result, data={"password": "secret"}),
                replace(result, error_code="untrusted text"), replace(result, external_reference="remote")):
            with self.assertRaises(ExecutionDenied):
                _result(action, invalid)

    def test_legacy_receipt_defaults_to_completed_and_failed_state_is_preserved(self):
        legacy = restored(SimpleNamespace(definition={"result": {"deleted": True}}))
        self.assertEqual(legacy.state, ResultState.COMPLETED)
        refused = restored(SimpleNamespace(definition={"state": "failed", "result": None, "error_code": "permission"}))
        self.assertEqual(refused.state, ResultState.FAILED)
        self.assertIsNone(refused.data)
