"""Тесты widget-credential и poll/send endpoints support-виджета (SPEC §7)."""

from __future__ import annotations

import json

from django.test import TestCase
from hub_platform.testing import TenantAPIClient as APIClient

from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import Department, Organization
from hub_platform.products.models import Product
from hub_platform.support.models import ContractStatus, ProductSupportContract
from hub_platform.support.test_helpers import FOXRAY_DATA, make_support_token
from hub_platform.webchat.testing import create_web_widget

SECRET = "test-support-secret-very-long-32bytes!!"


def _setup_support_channel(
    organization, support_department, product
) -> tuple[Channel, ProductSupportContract]:
    product.support_token_secret = SECRET
    product.save(update_fields=["support_token_secret"])
    contract = ProductSupportContract.objects.create(
        organization=organization,
        product=product,
        code="foxray.support.v1",
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
        code="foxray-support",
        name="FoxRay — поддержка",
        department=support_department,
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
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.support = Department.objects.get(organization=self.organization, code="support")
        self.product = Product.objects.get(organization=self.organization, code="foxray")
        self.channel, self.contract = _setup_support_channel(
            self.organization, self.support, self.product
        )
        self.widget = create_web_widget(self.channel, name="FoxRay support widget")
        self.client = APIClient()

    def _start_session(self) -> dict:
        token = make_support_token(secret=SECRET, data=FOXRAY_DATA)
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
