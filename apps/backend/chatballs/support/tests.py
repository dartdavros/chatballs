from __future__ import annotations

import json

from django.test import TestCase
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.channels.models import Channel
from chatballs.identity.audit import AuditResult
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import AuditEvent, Organization
from chatballs.products.models import Product
from chatballs.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)
from chatballs.support.test_helpers import FOXRAY_DATA, make_support_token
from chatballs.webchat.models import WebChatWidgetMode
from chatballs.webchat.testing import create_web_widget

SECRET = "test-support-secret-very-long-32bytes!!"


def _app_contract(organization, product) -> ProductSupportContract:
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
                        "email": {"type": "string", "format": "email"},
                    },
                },
                "clinic": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "name": {"type": "string"}},
                },
                "subscription": {
                    "type": "object",
                    "properties": {
                        "tariff": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
        },
        identity_mapping_json={
            "subject": "$.doctor.id",
            "account": "$.clinic.id",
            "display_name": "$.doctor.name",
            "display_email": "$.doctor.email",
        },
        operator_ui_json={
            "operator_cards": [
                {
                    "title": "Пользователь",
                    "fields": [{"label": "Имя", "path": "$.doctor.name", "type": "text"}],
                },
            ]
        },
        ai_context_json={"allowed_paths": ["$.doctor.name", "$.subscription.status"]},
        search_mapping_json={"paths": ["$.doctor.email", "$.doctor.name", "$.clinic.name"]},
        sensitive_fields_json={"paths": ["$.doctor.email"]},
    )
    return contract


class SupportSessionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.product = Product.objects.get(organization=self.organization, code="app")
        self.product.support_token_secret = SECRET
        self.product.save(update_fields=["support_token_secret"])
        self.contract = _app_contract(self.organization, self.product)
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="app-support",
            name="FoxRay — поддержка",
            product=self.product,
            requires_authenticated_product_identity=True,
            allow_anonymous_sessions=False,
            allow_self_reported_contact=False,
            allow_sales_attribution=False,
            allow_checkout_actions=False,
        )
        self.contract.allowed_channels.add(self.channel)
        self.widget = create_web_widget(self.channel, name="FoxRay support widget")
        self.client = APIClient()

    def _start(self, token: str, widget_key: str | None = None):
        return self.client.post(
            "/api/v1/support/sessions/",
            data=json.dumps({"widgetKey": widget_key or self.widget.public_key, "token": token}),
            content_type="application/json",
        )

    def test_happy_path_creates_snapshot_and_conversation(self) -> None:
        token = make_support_token(secret=SECRET, data=FOXRAY_DATA)
        response = self._start(token)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertIn("conversation", body)
        self.assertIn("snapshot", body)
        snapshot = SupportIdentitySnapshot.objects.get(subject_key="u_456")
        self.assertEqual(snapshot.contract_code, "app.support.v1")
        self.assertEqual(snapshot.display_name, "Иван Петров")
        self.assertEqual(snapshot.display_email, "doctor@example.com")
        self.assertEqual(snapshot.account_key, "c_123")
        self.assertIn("Иван Петров", snapshot.search_text)
        # AI context содержит только разрешённые пути.
        self.assertIn("$.doctor.name", snapshot.ai_context_json["allowed_paths"])
        self.assertNotIn("$.doctor.email", snapshot.ai_context_json["allowed_paths"])
        # Raw token не сохранён в snapshot.
        self.assertNotIn("token", json.dumps(snapshot.payload_json))
        self.assertTrue(snapshot.token_jti_hash)
        # Audit SUCCESS.
        self.assertTrue(
            AuditEvent.objects.filter(
                action="support.session_started", result=AuditResult.SUCCESS
            ).exists()
        )

    def test_invalid_signature_denied(self) -> None:
        token = make_support_token(secret="wrong-secret", data=FOXRAY_DATA)
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "support_unavailable")
        self._assert_denied_audit("TOKEN_SIGNATURE_INVALID")

    def test_expired_token_denied(self) -> None:
        token = make_support_token(secret=SECRET, data=FOXRAY_DATA, exp_delta=-100)
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("TOKEN_EXPIRED")

    def test_schema_error_denied(self) -> None:
        # Нет обязательного поля doctor.
        token = make_support_token(secret=SECRET, data={"clinic": {"id": "c_1"}})
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("PAYLOAD_SCHEMA_INVALID")

    def test_missing_subject_denied(self) -> None:
        # doctor.id пустой — schema проходит (ключ есть), но subject mapping пуст.
        token = make_support_token(
            secret=SECRET, data={"doctor": {"id": "", "email": "x@example.com"}}
        )
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("SUBJECT_MAPPING_EMPTY")

    def test_disabled_contract_denied(self) -> None:
        self.contract.status = ContractStatus.DISABLED
        self.contract.save(update_fields=["status"])
        token = make_support_token(secret=SECRET, data=FOXRAY_DATA)
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("CONTRACT_DISABLED")

    def test_wrong_channel_not_support(self) -> None:
        # Канал без support-политики (анонимные сессии разрешены) не может
        # принимать support-токен.
        sales_channel = Channel.objects.create(
            organization=self.organization, code="app-sales-x",
            name="FoxRay sales", product=self.product,
        )
        invalid_widget = create_web_widget(
            sales_channel,
            name="Invalid support widget",
            mode=WebChatWidgetMode.AUTHENTICATED_PRODUCT,
        )
        token = make_support_token(secret=SECRET, data=FOXRAY_DATA)
        response = self._start(token, widget_key=invalid_widget.public_key)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("CHANNEL_NOT_SUPPORT")

    def test_channel_product_mismatch_denied(self) -> None:
        # iss=site, но канал привязан к app.
        token = make_support_token(secret=SECRET, iss="site", data=FOXRAY_DATA)
        response = self._start(token)
        self.assertEqual(response.status_code, 422)
        self._assert_denied_audit("CHANNEL_PRODUCT_MISMATCH")

    def test_missing_token_denied(self) -> None:
        response = self.client.post(
            "/api/v1/support/sessions/",
            data=json.dumps({"widgetKey": self.widget.public_key}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "support_unavailable")

    def test_continue_session_reuses_open_conversation(self) -> None:
        token1 = make_support_token(secret=SECRET, data=FOXRAY_DATA, jti="jti-1")
        first = self._start(token1)
        self.assertEqual(first.status_code, 201)
        conv_id = first.json()["conversation"]["id"]
        # Повторный старт тем же subject → тот же открытый диалог.
        token2 = make_support_token(secret=SECRET, data=FOXRAY_DATA, jti="jti-2")
        second = self._start(token2)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["conversation"]["id"], conv_id)

    def test_raw_token_not_in_audit(self) -> None:
        token = make_support_token(secret="wrong-secret", data=FOXRAY_DATA, jti="secret-jti-xyz")
        self._start(token)
        denied = AuditEvent.objects.filter(action="support.session_denied").first()
        self.assertIsNotNone(denied)
        payload_str = json.dumps(denied.payload)
        # Raw токен и raw jti не должны попасть в audit — только хэш jti.
        self.assertNotIn(token, payload_str)
        self.assertNotIn("secret-jti-xyz", payload_str)

    def _assert_denied_audit(self, code: str) -> None:
        self.assertTrue(
            AuditEvent.objects.filter(
                action="support.session_denied",
                result=AuditResult.DENIED,
                payload__code=code,
            ).exists(),
            f"expected denied audit with code={code}",
        )


class SupportContractApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.product = Product.objects.get(organization=self.organization, code="app")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def test_owner_registers_contract(self) -> None:
        response = self.client.post(
            "/api/v1/support/contracts/",
            data=json.dumps({
                "code": "app.support.v2",
                "productId": self.product.id,
                "status": "DRAFT",
                "schemaJson": {},
                "identityMappingJson": {"subject": "$.user.id"},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["contract"]["code"], "app.support.v2")
        self.assertEqual(response.json()["contract"]["version"], 2)

    def test_operator_cannot_register_contract(self) -> None:
        # Оператор (роль EMPLOYEE) не имеет прав на управление контрактами.
        self.client.login(username="staff.member@example.org", password="Operator-Local-2026")
        response = self.client.post(
            "/api/v1/support/contracts/",
            data=json.dumps({"code": "app.support.v3", "productId": self.product.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_contract_code_must_match_product(self) -> None:
        response = self.client.post(
            "/api/v1/support/contracts/",
            data=json.dumps({"code": "site.support.v1", "productId": self.product.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("code", response.json()["detail"].lower())
