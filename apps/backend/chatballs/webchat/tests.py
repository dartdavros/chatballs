import json

from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization
from chatballs.webchat.models import WebSession
from chatballs.webchat.testing import create_web_widget


class PublicWebChatWidgetTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(
            email="webchat-owner@example.com",
            password="temporary-password",
        )
        self.organization = Organization.objects.get(slug="demo")
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="website-chat",
            name="Чат сайта",
        )
        self.client = APIClient()

    def _session(self, widget_key: str, host_origin: str = ""):
        return self.client.post(
            "/api/v1/webchat/session/",
            data=json.dumps(
                {
                    "widgetKey": widget_key,
                    "hostOrigin": host_origin,
                }
            ),
            content_type="application/json",
        )

    def test_widgets_on_same_channel_have_independent_entry_points(self) -> None:
        first = create_web_widget(self.channel, name="Первый виджет")
        second = create_web_widget(self.channel, name="Второй виджет")

        first_config = self.client.get(
            "/api/v1/webchat/config/",
            {"widgetKey": first.public_key},
        )
        second_config = self.client.get(
            "/api/v1/webchat/config/",
            {"widgetKey": second.public_key},
        )

        self.assertTrue(first_config.json()["available"])
        self.assertTrue(second_config.json()["available"])
        self.assertEqual(first_config.json()["widgetKey"], first.public_key)
        self.assertEqual(second_config.json()["widgetKey"], second.public_key)

        first_session = self._session(first.public_key)
        second_session = self._session(second.public_key)
        self.assertEqual(first_session.status_code, 201)
        self.assertEqual(second_session.status_code, 201)
        self.assertSetEqual(
            set(WebSession.objects.values_list("widget_id", flat=True)),
            {first.id, second.id},
        )

    def test_legacy_channel_alias_is_unavailable_when_ambiguous(self) -> None:
        create_web_widget(self.channel, name="Первый виджет")
        create_web_widget(self.channel, name="Второй виджет")

        response = self.client.get(
            "/api/v1/webchat/config/",
            {"channel": self.channel.code},
        )

        self.assertEqual(response.json(), {"available": False})

    def test_voice_message_round_trip(self) -> None:
        # Голосовое из виджета: multipart → VOICE-сообщение, диалог уходит
        # оператору; аудио отдаётся только владельцу токена сессии.
        from django.core.files.uploadedfile import SimpleUploadedFile

        from chatballs.conversations.models import (
            ControlMode,
            Conversation,
            MessageKind,
        )

        widget = create_web_widget(self.channel, name="Виджет")
        token = self._session(widget.public_key).json()["token"]

        posted = self.client.post(
            "/api/v1/webchat/messages/",
            data={
                "audio": SimpleUploadedFile("voice.webm", b"WEBMDATA", content_type="audio/webm"),
                "duration": "4",
            },
            format="multipart",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(posted.status_code, 201)

        conversation = Conversation.objects.get(channel=self.channel)
        message = conversation.messages.get(kind=MessageKind.VOICE)
        self.assertEqual(message.duration_seconds, 4)
        self.assertTrue(message.audio)
        self.assertEqual(conversation.control_mode, ControlMode.PAUSED)

        payload = self.client.get(
            "/api/v1/webchat/messages/?since=0",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        voice = next(m for m in payload["messages"] if m["kind"] == MessageKind.VOICE)
        self.assertTrue(voice["hasAudio"])
        self.assertEqual(voice["durationSeconds"], 4)

        audio = self.client.get(f"/api/v1/webchat/messages/{message.id}/audio/?token={token}")
        self.assertEqual(audio.status_code, 200)
        self.assertEqual(audio.headers["Content-Type"], "audio/webm")

        # Чужая сессия не видит аудио этого диалога.
        foreign_token = self._session(widget.public_key).json()["token"]
        denied = self.client.get(f"/api/v1/webchat/messages/{message.id}/audio/?token={foreign_token}")
        self.assertEqual(denied.status_code, 404)

    def test_widget_origin_policy_is_scoped_per_widget(self) -> None:
        allowed = create_web_widget(
            self.channel,
            name="Портал",
            allowed_origins=["https://help.example.test"],
        )
        denied = create_web_widget(
            self.channel,
            name="Кабинет",
            allowed_origins=["https://cabinet.example.test"],
        )

        self.assertEqual(
            self._session(allowed.public_key, "https://help.example.test/article").status_code,
            201,
        )
        self.assertEqual(
            self._session(denied.public_key, "https://help.example.test/article").status_code,
            404,
        )

