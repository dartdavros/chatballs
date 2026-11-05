"""Aggregate errors are localized without rewriting adapter business values."""

from django.test import SimpleTestCase

from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.result_payloads import display_errors


class ResultPayloadTests(SimpleTestCase):
    def test_only_structural_error_slots_are_translated(self):
        block = {"kind": "foreach", "body": [{"id": "read", "kind": "action"}]}
        business = {"error": {"reason": "arguments"}}
        value = {"items": [{"index": 0, "state": "failed", "steps": {"read": business},
                            "error": {"reason": "arguments"}}], "errors": []}
        result = display_errors(value, block)
        self.assertEqual(result["items"][0]["error"]["reason"], error_message("arguments"))
        self.assertEqual(result["items"][0]["steps"]["read"], business)
        self.assertEqual(value["items"][0]["error"]["reason"], "arguments")
