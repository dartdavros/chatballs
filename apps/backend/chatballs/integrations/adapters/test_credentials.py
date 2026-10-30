"""Границы защиты вложенных credentials и клиентского TLS-доступа."""

from dataclasses import replace
from types import SimpleNamespace

from django.test import SimpleTestCase

from chatballs.ai.diagnostic_redaction import REDACTED, DiagnosticRedactor, integration_secrets
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.integrations.adapters.auth import AuthExtension, OutboundRequest, split_values
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.adapters.transport import TransportError, _redirected
from chatballs.integrations.service_connections.binding import dump_credentials


class CredentialBoundaryTests(SimpleTestCase):
    def test_nested_secret_branch_is_encrypted_and_redacted_as_a_whole(self):
        fields = TypeSpec("object", properties=(
            ("region", TypeSpec("string")),
            ("accounts", TypeSpec("array", items=TypeSpec("object", properties=(
                ("key", TypeSpec("string", secret=True)), ("label", TypeSpec("string")),
            )))),
        ))
        accounts = [{"key": "NestedCredential12345", "label": "Primary account"}]
        settings, credentials = split_values(fields, {"region": "eu", "accounts": accounts})
        self.assertEqual(settings, {"region": "eu"})
        self.assertEqual(credentials, {"accounts": accounts})
        self.assertIn("NestedCredential12345", AuthExtension().secrets(credentials))
        integration = SimpleNamespace(secret="", config={}, secret_headers="", service_settings=SimpleNamespace(
            credentials=dump_credentials(credentials),
        ))
        redactor = DiagnosticRedactor(Pseudonymizer({}), secrets=integration_secrets([integration]))
        self.assertEqual(redactor.text("access=NestedCredential12345"), f"access={REDACTED}")

    def test_cross_origin_redirect_cannot_send_client_certificate(self):
        request = OutboundRequest("POST", "https://service.test/api", client_certificate=("certificate", "key"))
        self.assertEqual(_redirected(request, 307, "https://service.test/next").client_certificate, request.client_certificate)
        with self.assertRaises(TransportError) as caught:
            _redirected(request, 307, "https://other.test/next")
        self.assertEqual(caught.exception.code, "address_forbidden")
        anonymous = _redirected(replace(request, client_certificate=None, headers={"Authorization": "Bearer x"}), 307,
                               "https://other.test/next")
        self.assertNotIn("Authorization", anonymous.headers)
