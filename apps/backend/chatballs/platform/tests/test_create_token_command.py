from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from chatballs.platform.models import PlatformOperator, PlatformToken
from chatballs.platform.tokens import authenticate_token


class CreatePlatformTokenCommandTests(TestCase):
    def test_creates_operator_and_returns_plaintext_once(self) -> None:
        out = StringIO()
        call_command(
            "create_platform_token",
            name="Ops Alice",
            token_name="ci",
            capabilities=["platform.organizations.provision"],
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("Ops Alice", output)
        # Plaintext token line present.
        plaintext = [line for line in output.splitlines() if line.startswith("ctp_")]
        self.assertEqual(len(plaintext), 1)
        token_value = plaintext[0]
        # Only the hash is stored, never the plaintext.
        self.assertFalse(PlatformToken.objects.filter(token_hash=token_value).exists())
        # The stored hash authenticates.
        operator = PlatformOperator.objects.get(name="Ops Alice")
        token = authenticate_token(token_value)
        self.assertIsNotNone(token)
        self.assertEqual(token.operator_id, operator.id)
        self.assertIn("platform.organizations.provision", token.capabilities)

    def test_unknown_capability_is_rejected(self) -> None:
        with self.assertRaises(CommandError):
            call_command(
                "create_platform_token", name="Ops Bob", capabilities=["bogus.code"]
            )
