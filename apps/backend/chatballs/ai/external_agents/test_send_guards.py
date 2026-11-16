"""Revoke authority at the final in-process HTTP/SMTP transport boundary."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.external_agents import delivery, dispatch
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.ai.provider.base import ProviderRejected
from chatballs.conversations.transports.base import request_json
from chatballs.conversations.transports.email_smtp import deliver_message
from chatballs.integrations.adapters.transport import GuardedTransport


class SendGuardTests(RuntimeData, TestCase):
    def takeover(self):
        self.conversation.control_mode = "HUMAN"
        self.conversation.save(update_fields=["control_mode"])

    def test_http_rechecks_after_connect_before_export(self):
        row = self.request()
        # Configuration setup patches send; exercise the real implementation here.
        wire = Mock()

        def connected(*args):
            self.takeover()
            return wire

        from chatballs.integrations.adapters import transport

        with patch.object(GuardedTransport, "send", _REAL_SEND), patch.object(transport, "check_tool_url"), \
                patch.object(transport, "_connected", side_effect=connected), \
                patch("chatballs.ai.external_agents.recovery.cancel_due"):
            dispatch.run(self.context, self.conversation.pk)
        wire.request.assert_not_called()
        wire.close.assert_called_once()
        row.refresh_from_db()
        self.assertEqual(row.state, "cancelled")

    def test_native_http_guard_precedes_open(self):
        with patch("chatballs.conversations.transports.base.build_opener") as opener:
            allowed = iter((True, False))
            with self.assertRaises(ProviderRejected), execution_guard(lambda: next(allowed)):
                request_json("https://transport.example.invalid", method="POST", body={"text": "reply"})
        opener.assert_not_called()

    def test_smtp_rechecks_after_login_before_message(self):
        smtp = Mock()
        allowed = True

        def login(*args):
            nonlocal allowed
            allowed = False

        smtp.login.side_effect = login
        integration = SimpleNamespace(is_active=True, config={"smtp_host": "mail.example.invalid"}, secret="test-only")
        with patch("chatballs.conversations.transports.email_smtp.smtplib.SMTP_SSL", return_value=smtp):
            with self.assertRaises(ProviderRejected), execution_guard(lambda: allowed):
                deliver_message(integration, Mock())
        smtp.send_message.assert_not_called()
        smtp.quit.assert_called_once()

    def test_delivery_rechecks_after_work_preparation(self):
        row = self.request()
        self.claim()
        self.accept(row, self.result(row))
        original = delivery.claim

        def claimed(*args):
            work = original(*args)
            self.takeover()
            return work

        with patch.object(delivery, "claim", side_effect=claimed):
            self.deliver(times=1)
        self.sender.assert_not_called()
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "suppressed")

    def test_transport_configuration_roundtrip_revokes_route(self):
        row = self.request()
        self.claim()
        for config in ({"base_url": "https://changed.example.invalid"}, {}):
            self.messaging.config = config
            self.messaging.save(update_fields=["config"])
        ack, _ = self.accept(row, self.result(row))
        self.assertEqual(ack["state"], "suppressed")


_REAL_SEND = GuardedTransport.send
