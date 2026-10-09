import json

from django.test import SimpleTestCase

from chatballs.ai.diagnostic_redaction import REDACTED, DiagnosticRedactor
from chatballs.ai.pseudonymization import Pseudonymizer, contact_known_values


class DiagnosticRedactionTests(SimpleTestCase):
    def setUp(self):
        self.redactor = DiagnosticRedactor(Pseudonymizer(contact_known_values(
            name="Анна", email="anna@example.ru", phone="+79990001122",
        )), ["actual-site-credential", "provider-key-123"])

    def test_credentials_are_removed_from_nested_data_and_embedded_json(self):
        value = self.redactor.clean({
            "session_token": "never-known-secret", "args": {"id": "51621"},
            "response": '{"access_token":"upstream-secret","status":"paid"}',
            "error": "request failed: provider-key-123 actual-site-credential",
            "prompt": "session_token=arbitrary-secret Bearer arbitrary-bearer",
        })
        encoded = json.dumps(value)
        for secret in ("never-known-secret", "upstream-secret", "provider-key-123",
                       "actual-site-credential", "arbitrary-secret", "arbitrary-bearer"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(value["args"]["id"], "51621")
        self.assertIn("paid", value["response"])

    def test_urls_strip_credentials_query_values_and_fragments(self):
        value = self.redactor.text("GET https://user:password@example.test/orders/51621?session_token=abc&q=xyz#secret")
        for secret in ("user:password", "abc", "xyz", "#secret"):
            self.assertNotIn(secret, value)
        self.assertIn("example.test/orders/51621", value)

    def test_personal_data_are_masked_and_existing_tokens_preserved(self):
        value = self.redactor.text("Анна anna@example.ru +79990001122 [[client_name]]")
        self.assertEqual(value.count("[[client_name]]"), 2)
        self.assertIn("[[client_email]]", value)
        self.assertNotIn("anna@example.ru", value)

    def test_large_data_have_an_explicit_size_limit(self):
        self.redactor.remaining = 20
        value = self.redactor.text("я" * 100)
        self.assertTrue(self.redactor.truncated)
        self.assertEqual(self.redactor.remaining, 0)
        self.assertTrue(value.endswith("[truncated]"))
        self.assertEqual(self.redactor.clean({"secret": "a"}), {"secret": REDACTED})

    def test_exhausted_budget_preserves_structure_and_numeric_token_counts(self):
        self.redactor.remaining = 0
        value = self.redactor.clean({"prompt_tokens": 10, "messages": [{"role": "user", "content": "abc"}]})
        self.assertEqual(value["prompt_tokens"], 10)
        self.assertIn("content", value["messages"][0])

    def test_secret_dictionary_keys_and_numeric_secrets_are_removed(self):
        self.redactor.secrets.append("10482")
        value = self.redactor.clean({"provider-key-123": "value", "bound": 10482})
        self.assertNotIn("provider-key-123", json.dumps(value))
        self.assertEqual(value["bound"], REDACTED)

    def test_deep_external_json_is_truncated_without_recursion_failure(self):
        value = {"status": "paid"}
        for _ in range(100):
            value = {"nested": value}
        self.assertIn("[truncated]", json.dumps(self.redactor.clean(value)))
        self.assertTrue(self.redactor.truncated)
