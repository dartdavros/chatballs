"""The 256 KiB budget never sends a partial replace or truncates an element."""

from django.test import TestCase

from chatballs.ai.external_agents.context import fit_window
from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.custom_fields import snapshot
from chatballs.ai.external_agents.json_payloads import dumps, size


class ContextBudgetTests(ContextData, TestCase):
    def test_full_replace_over_budget_blocks_dispatch_without_cutting_items(self):
        definitions = [{"key": f"field_{i}", "label": "Field", "type": "string"} for i in range(30)]
        sources = [self.source(definitions, name=f"Source {i}") for i in range(8)]
        for source in sources:
            for definition in source.config["fields"]:
                self.value(source, definition["key"], "я" * 500)
        self.grant(*sources)
        complete = snapshot(self.binding(), self.contact)
        self.assertEqual((len(complete["scope"]), len(complete["items"])), (240, 240))
        self.assertGreater(size(complete), 262144)
        row = self.request()
        self.assertIsNone(self.claim())
        row.refresh_from_db()
        self.assertEqual((row.attempts, row.reason_code, row.snapshot_ciphertext), (0, "payload_too_large", ""))

    def test_exact_transport_limit_is_accepted_and_one_byte_more_is_refused(self):
        row = self.request("x")
        work = self.claim()
        self.assertIsNotNone(work)
        data = self.frozen(row)
        overhead = len(work.request.body) - 1
        self.assertEqual(size(data), len(work.request.body))
        self.assertNotIn("name", data["context"]["customer"]["fields"])
        self.assertEqual(dumps(data).encode(), work.request.body)
        data["trigger"]["text"] = "x" * (262144 - overhead)
        fit_window(data, [], row)
        self.assertEqual(size(data), 262144)
        data["trigger"]["text"] += "x"
        with self.assertRaisesRegex(ValueError, "payload_too_large"):
            fit_window(data, [], row)
