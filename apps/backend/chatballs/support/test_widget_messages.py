"""Тесты widget-credential и poll/send endpoints support-виджета (SPEC §7)."""

from __future__ import annotations

import json

from django.test import TestCase
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.products.models import Product
from chatballs.support.models import ContractStatus, ProductSupportContract
from chatballs.support.test_helpers import ACME_DATA, make_support_token
from chatballs.webchat.testing import create_web_widget

SECRET = "test-support-secret-very-long-32bytes!!"


def _setup_support_channel(
    organization, product
) -> tuple[Channel, ProductSupportContract]:
    product.support_token_secret = SECRET
    product.save(update_fields=["support_token_secret"])
    contract = ProductSupportContract.objects.create(
        organization=organization,
        product=product,
        code="app.support.v1",
        version=1,
        status=ContractStatus.ACTIVE,
        schema_json={
            "type": "object",
            "required": ["doctor"],
            "properties": {
                "doctor": {
                    "type": "object",
                    "required": ["id", "email"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                }
            },
        },
        identity_mapping_json={
            "subject": "$.doctor.id",
            "display_name": "$.doctor.name",
            "display_email": "$.doctor.email",
        },
        operator_ui_json={"operator_cards": []},
        ai_context_json={"allowed_paths": ["$.doctor.name"]},
        search_mapping_json={"paths": ["$.doctor.email"]},
        sensitive_fields_json={"paths": []},
    )
    channel = Channel.objects.create(
        organization=organization,
        code="app-support",
        name="Acme — поддержка",
        product=product,
        requires_authenticated_product_identity=True,
        allow_anonymous_sessions=False,
        allow_self_reported_contact=False,
        allow_sales_attribution=False,
        allow_checkout_actions=False,
    )
    contract.allowed_channels.add(channel)
    return channel, contract


class SupportWidgetMessagesTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.product = Product.objects.get(organization=self.organization, code="app")
        self.channel, self.contract = _setup_support_channel(
            self.organization, self.product
        )
        self.widget = create_web_widget(self.channel, name="Acme support widget")
        self.client = APIClient()

    def _start_session(self) -> dict:
        token = make_support_token(secret=SECRET, data=ACME_DATA)
        response = self.client.post(
            "/api/v1/support/sessions/",
            data=json.dumps({"widgetKey": self.widget.public_key, "token": token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def _send(self, credential: str, conversation_id: int, text: str = "Не работает импорт"):
        return self.client.post(
            "/api/v1/support/sessions/messages/",
            data=json.dumps({"conversation": conversation_id, "text": text}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {credential}",
        )

    def _poll(self, credential: str, since: int = 0):
        return self.client.get(
            f"/api/v1/support/sessions/messages/?since={since}",
            HTTP_AUTHORIZATION=f"Bearer {credential}",
        )

    def test_session_issues_widget_credential(self) -> None:
        body = self._start_session()
        self.assertIn("widgetCredential", body)
        self.assertTrue(body["widgetCredential"])
        self.assertEqual(body["conversation"]["id"], body["conversation"]["id"])

    def test_send_and_poll_returns_messages(self) -> None:
        body = self._start_session()
        credential = body["widgetCredential"]
        conversation_id = body["conversation"]["id"]
        send_resp = self._send(credential, conversation_id)
        self.assertEqual(send_resp.status_code, 201, send_resp.content)
        # Poll возвращает сообщение клиента (AI может не ответить без провайдера в тестах).
        poll_resp = self._poll(credential)
        self.assertEqual(poll_resp.status_code, 200, poll_resp.content)
        texts = [m["text"] for m in poll_resp.json()["messages"]]
        self.assertIn("Не работает импорт", texts)

    def test_invalid_credential_rejected(self) -> None:
        self._start_session()
        resp = self._poll("invalid.credential")
        self.assertEqual(resp.status_code, 401)

    def test_send_without_credential_rejected(self) -> None:
        body = self._start_session()
        resp = self.client.post(
            "/api/v1/support/sessions/messages/",
            data=json.dumps({"conversation": body["conversation"]["id"], "text": "x"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_empty_message_rejected(self) -> None:
        body = self._start_session()
        resp = self._send(body["widgetCredential"], body["conversation"]["id"], "  ")
        self.assertEqual(resp.status_code, 400)

    def test_voice_and_file_round_trip(self) -> None:
        from unittest import mock

        from django.core.files.uploadedfile import SimpleUploadedFile

        from chatballs.conversations.models import ControlMode, Conversation, MessageKind

        body = self._start_session()
        self.assertTrue(body["features"]["voiceMessages"])
        credential = body["widgetCredential"]
        # Голосовое: стенограмма → AI отвечает текстом.
        with (
            mock.patch("chatballs.ai.provider.local.LocalProvider.transcribe", return_value="Не работает импорт"),
            mock.patch("chatballs.support.messages.run_channel_turn", return_value=mock.Mock(text="Проверьте формат файла.")) as run,
        ):
            posted = self.client.post(
                "/api/v1/support/sessions/messages/",
                data={"audio": SimpleUploadedFile("voice.webm", b"WEBMDATA", content_type="audio/webm"), "duration": "3"},
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {credential}",
            )
        self.assertEqual(posted.status_code, 201, posted.content)
        self.assertEqual(run.call_args.kwargs["message"], "Не работает импорт")
        conversation = Conversation.objects.get(id=body["conversation"]["id"])
        voice = conversation.messages.get(kind=MessageKind.VOICE)
        self.assertEqual(voice.transcript, "Не работает импорт")
        items = self._poll(credential).json()["messages"]
        voice_item = next(m for m in items if m["kind"] == MessageKind.VOICE)
        self.assertTrue(voice_item["hasAudio"])
        self.assertEqual(voice_item["durationSeconds"], 3)
        self.assertIn("Проверьте формат файла.", [m["text"] for m in items])
        audio = self.client.get(f"/api/v1/support/sessions/messages/{voice.id}/audio/?credential={credential}")
        self.assertEqual(audio.status_code, 200)
        self.assertEqual(audio.headers["Content-Type"], "audio/webm")
        self.assertEqual(self.client.get(f"/api/v1/support/sessions/messages/{voice.id}/audio/?credential=bad").status_code, 401)

        # Файл без подписи — диалог оператору; вложение отдаётся по credential.
        posted = self.client.post(
            "/api/v1/support/sessions/messages/",
            data={"file": SimpleUploadedFile("лог.txt", b"error", content_type="text/plain")},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {credential}",
        )
        self.assertEqual(posted.status_code, 201, posted.content)
        conversation.refresh_from_db()
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)
        attachment = conversation.messages.get(kind=MessageKind.FILE)
        item = next(m for m in self._poll(credential).json()["messages"] if m["kind"] == MessageKind.FILE)
        self.assertEqual(item["attachment"]["name"], "лог.txt")
        served = self.client.get(f"/api/v1/support/sessions/messages/{attachment.id}/attachment/?credential={credential}")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(b"".join(served.streaming_content), b"error")

    def test_voice_disabled_for_entry_point(self) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.widget.integration.voice_messages_enabled = False
        self.widget.integration.save(update_fields=["voice_messages_enabled"])
        body = self._start_session()
        self.assertFalse(body["features"]["voiceMessages"])
        posted = self.client.post(
            "/api/v1/support/sessions/messages/",
            data={"audio": SimpleUploadedFile("voice.webm", b"WEBMDATA", content_type="audio/webm")},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {body['widgetCredential']}",
        )
        self.assertEqual(posted.status_code, 400)

