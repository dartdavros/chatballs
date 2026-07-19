import json

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from hub_platform.testing import TenantAPIClient as APIClient

from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.capabilities import ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    Department,
    EmployeeAccessAssignment,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from hub_platform.products.models import Product

SALES_POLICY = {
    "requiresAuthenticatedProductIdentity": False,
    "allowAnonymousSessions": True,
    "allowSelfReportedContact": True,
    "allowSalesAttribution": True,
    "allowCheckoutActions": True,
}
OPERATOR_POLICY = {
    "requiresAuthenticatedProductIdentity": False,
    "allowAnonymousSessions": True,
    "allowSelfReportedContact": True,
    "allowSalesAttribution": False,
    "allowCheckoutActions": False,
}


def _make_channel(organization, *, code, name, **extra):
    extra.setdefault("allow_sales_attribution", False)
    extra.setdefault("allow_checkout_actions", False)
    return Channel.objects.create(organization=organization, code=code, name=name, **extra)


def _messenger(organization, *, name="Bot", channel=None):
    return Integration.objects.create(
        organization=organization,
        kind=IntegrationKind.MESSENGER,
        provider=IntegrationProvider.TELEGRAM,
        name=name,
        channel=channel,
    )


class ChannelApiTestCase(TestCase):
    """Общий владелец и клиент: owner имеет все capability по роли."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales = Department.objects.get(organization=self.organization, code="sales")
        self.support = Department.objects.get(
            organization=self.organization, code="support"
        )
        self.product = Product.objects.get(organization=self.organization, code="foxray")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def post_channel(self, **overrides):
        body = {
            "code": "partners",
            "name": "Партнёрская линия",
            "departmentId": None,
            "productId": None,
            "policyPreset": "CUSTOM",
            "policy": OPERATOR_POLICY,
        }
        body.update(overrides)
        return self.client.post(
            "/api/v1/channels/", data=json.dumps(body), content_type="application/json"
        )

    def patch_channel(self, channel_id: int, **body):
        return self.client.patch(
            f"/api/v1/channels/{channel_id}/",
            data=json.dumps(body),
            content_type="application/json",
        )


class ChannelCreateTests(ChannelApiTestCase):
    def test_creates_operator_channel_without_agent(self) -> None:
        response = self.post_channel()

        self.assertEqual(response.status_code, 201)
        channel = response.json()["channel"]
        self.assertEqual(channel["code"], "partners")
        # Канал без агента — валидное операторское состояние (ADR-HUB-0037 §5).
        self.assertIsNone(channel["agent"])
        self.assertEqual(channel["connections"], [])
        self.assertTrue(channel["isActive"])
        self.assertTrue(Channel.objects.filter(code="partners").exists())
        self.assertFalse(AIAgent.objects.exists())

    def test_payload_carries_no_agent_configuration_or_knowledge(self) -> None:
        response = self.post_channel()

        channel = response.json()["channel"]
        forbidden = {
            "persona", "tone", "instructions", "model", "credentialMode",
            "allowedTools", "limits", "knowledgeIds", "knowledge", "knowledgeCount",
        }
        self.assertEqual(forbidden & set(channel), set())

    def test_sales_preset_fills_policy(self) -> None:
        response = self.post_channel(
            code="foxray-sales",
            name="FoxRay — продажи",
            productId=self.product.id,
            departmentId=self.sales.id,
            policyPreset="SALES",
            policy=None,
        )
        # policy=None остаётся ключом в теле, поэтому пресет и явная политика
        # конфликтуют — проверяем именно чистый пресет.
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/v1/channels/",
            data=json.dumps(
                {
                    "code": "foxray-sales",
                    "name": "FoxRay — продажи",
                    "productId": self.product.id,
                    "departmentId": self.sales.id,
                    "policyPreset": "SALES",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["channel"]["policy"], SALES_POLICY)

    def test_rejects_duplicate_code(self) -> None:
        self.post_channel()
        response = self.post_channel(name="Другая линия")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Channel.objects.filter(code="partners").count(), 1)

    def test_rejects_invalid_code(self) -> None:
        for code in ("Partners", "-partners", "парт", "a" * 65, ""):
            with self.subTest(code=code):
                response = self.post_channel(code=code)
                self.assertEqual(response.status_code, 400)

    def test_policy_invariants_reject_the_whole_request(self) -> None:
        # P1/P2: непродуктовый канал не формирует коммерческих действий.
        response = self.post_channel(productId=None, policy=SALES_POLICY)

        self.assertEqual(response.status_code, 400)
        rules = {item["rule"] for item in response.json()["violations"]}
        self.assertEqual(rules, {"P1", "P2"})
        self.assertFalse(Channel.objects.filter(code="partners").exists())

    def test_authenticated_identity_conflicts_with_anonymous_sessions(self) -> None:
        response = self.post_channel(
            productId=self.product.id,
            policy={**SALES_POLICY, "requiresAuthenticatedProductIdentity": True},
        )

        self.assertEqual(response.status_code, 400)
        rules = {item["rule"] for item in response.json()["violations"]}
        self.assertEqual(rules, {"P4", "P5"})

    def test_support_preset_requires_product(self) -> None:
        response = self.client.post(
            "/api/v1/channels/",
            data=json.dumps(
                {"code": "helpline", "name": "Поддержка", "policyPreset": "SUPPORT"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            {item["rule"] for item in response.json()["violations"]}, {"P3"}
        )


class ChannelUpdateTests(ChannelApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = _make_channel(
            self.organization, code="firepage-sales", name="FirePage — продажи"
        )

    def test_renames_channel_and_keeps_code(self) -> None:
        response = self.patch_channel(self.channel.id, name="FirePage — продажи 2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"]["name"], "FirePage — продажи 2")
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.code, "firepage-sales")

    def test_rejects_empty_name(self) -> None:
        self.assertEqual(self.patch_channel(self.channel.id, name="   ").status_code, 400)

    def test_rejects_code_change(self) -> None:
        response = self.patch_channel(self.channel.id, code="renamed")

        self.assertEqual(response.status_code, 400)
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.code, "firepage-sales")

    def test_ignores_unchanged_code(self) -> None:
        response = self.patch_channel(
            self.channel.id, code="firepage-sales", name="Ещё имя"
        )
        self.assertEqual(response.status_code, 200)

    def test_changes_product_status_and_policy(self) -> None:
        response = self.patch_channel(
            self.channel.id,
            productId=self.product.id,
            isActive=False,
            policy={"allowCheckoutActions": True},
        )

        self.assertEqual(response.status_code, 200)
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.product_id, self.product.id)
        self.assertFalse(self.channel.is_active)
        self.assertTrue(self.channel.allow_checkout_actions)

    def test_deactivation_warns_about_active_agent(self) -> None:
        AIAgent.objects.create(
            channel=self.channel,
            name="FirePage Agent",
            status=AIAgentStatus.ACTIVE,
            model="openai/gpt-4o-mini",
        )
        response = self.patch_channel(self.channel.id, isActive=False)

        self.assertEqual(response.status_code, 200)
        warnings = response.json()["warnings"]
        self.assertEqual(warnings[0]["code"], "agent_still_active")

    def test_rejects_unknown_policy_flag(self) -> None:
        response = self.patch_channel(self.channel.id, policy={"allowEverything": True})
        self.assertEqual(response.status_code, 400)

    def test_other_organization_channel_is_not_found(self) -> None:
        other = Organization.objects.create(slug="other", name="Other")
        other_channel = _make_channel(other, code="other-sales", name="Other — продажи")

        response = self.patch_channel(other_channel.id, name="Взлом")

        self.assertEqual(response.status_code, 404)
        other_channel.refresh_from_db()
        self.assertEqual(other_channel.name, "Other — продажи")


class ChannelDeleteTests(ChannelApiTestCase):
    def test_deletes_channel_without_references(self) -> None:
        channel = _make_channel(self.organization, code="typo", name="Опечатка")

        response = self.client.delete(f"/api/v1/channels/{channel.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Channel.objects.filter(id=channel.id).exists())

    def test_blocks_deletion_with_references(self) -> None:
        channel = _make_channel(self.organization, code="live", name="Живой")
        _messenger(self.organization, channel=channel)
        AIAgent.objects.create(
            channel=channel, name="Agent", status=AIAgentStatus.DRAFT,
            model="openai/gpt-4o-mini",
        )

        response = self.client.delete(f"/api/v1/channels/{channel.id}/")

        self.assertEqual(response.status_code, 409)
        blockers = {item["type"]: item["count"] for item in response.json()["blockers"]}
        self.assertEqual(blockers, {"connections": 1, "agent": 1})
        self.assertTrue(Channel.objects.filter(id=channel.id).exists())


class ChannelConnectionTests(ChannelApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = _make_channel(self.organization, code="main", name="Основной")
        self.integration = _messenger(self.organization, name="Telegram Bot")

    def _bind(self, channel_id: int, integration_id: int, **body):
        return self.client.post(
            f"/api/v1/channels/{channel_id}/connections/",
            data=json.dumps({"integrationId": integration_id, **body}),
            content_type="application/json",
        )

    def test_binds_and_unbinds_connection(self) -> None:
        response = self._bind(self.channel.id, self.integration.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["channel"]["connections"]), 1)

        response = self.client.delete(
            f"/api/v1/channels/{self.channel.id}/connections/{self.integration.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"]["connections"], [])
        self.integration.refresh_from_db()
        self.assertIsNone(self.integration.channel_id)

    def test_rejects_llm_provider_as_connection(self) -> None:
        provider = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.LLM_PROVIDER,
            provider=IntegrationProvider.OPENROUTER,
            name="OpenRouter",
        )

        self.assertEqual(self._bind(self.channel.id, provider.id).status_code, 400)

    def test_rejects_binding_to_archived_channel(self) -> None:
        self.channel.is_active = False
        self.channel.save(update_fields=["is_active"])

        self.assertEqual(self._bind(self.channel.id, self.integration.id).status_code, 400)

    def test_move_between_channels_requires_force(self) -> None:
        other = _make_channel(self.organization, code="second", name="Второй")
        self._bind(self.channel.id, self.integration.id)

        response = self._bind(other.id, self.integration.id)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "connection_already_bound")
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.channel_id, self.channel.id)

        response = self._bind(other.id, self.integration.id, force=True)
        self.assertEqual(response.status_code, 200)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.channel_id, other.id)


class ChannelListTests(ChannelApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.sales_channel = _make_channel(
            self.organization, code="foxray-sales", name="FoxRay — продажи",
            department=self.sales, product=self.product,
        )
        self.orphan = _make_channel(self.organization, code="edevs", name="Edevs — сайт")
        self.archived = _make_channel(
            self.organization, code="old", name="Старый", is_active=False
        )

    def test_lists_all_channels_for_owner(self) -> None:
        response = self.client.get("/api/v1/channels/")

        self.assertEqual(response.status_code, 200)
        codes = {item["code"] for item in response.json()["items"]}
        self.assertEqual(codes, {"foxray-sales", "edevs", "old"})

    def test_filters_by_department_product_and_status(self) -> None:
        cases = (
            ({"department": "none"}, {"edevs", "old"}),
            ({"department": str(self.sales.id)}, {"foxray-sales"}),
            ({"product": "none"}, {"edevs", "old"}),
            ({"isActive": "false"}, {"old"}),
            ({"hasAgent": "false"}, {"foxray-sales", "edevs", "old"}),
            ({"q": "прода"}, {"foxray-sales"}),
        )
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/channels/", params)
                codes = {item["code"] for item in response.json()["items"]}
                self.assertEqual(codes, expected)

    def test_counters_do_not_issue_a_query_per_channel(self) -> None:
        # §6.1: счётчик открытых диалогов — один агрегат на список. Проверяем
        # само свойство, а не абсолютное число: рост каналов не должен менять
        # количество запросов.
        def count_queries() -> int:
            with CaptureQueriesContext(connection) as captured:
                response = self.client.get("/api/v1/channels/")
                self.assertEqual(response.status_code, 200)
            return len(captured)

        baseline = count_queries()
        for index in range(5):
            _make_channel(
                self.organization, code=f"extra-{index}", name=f"Канал {index}"
            )

        self.assertEqual(len(self.client.get("/api/v1/channels/").json()["items"]), 8)
        self.assertEqual(count_queries(), baseline)


class ChannelScopeTests(ChannelApiTestCase):
    """§5.2 — department-scoped доступ."""

    def setUp(self) -> None:
        super().setUp()
        self.sales_channel = _make_channel(
            self.organization, code="foxray-sales", name="FoxRay — продажи",
            department=self.sales, product=self.product,
        )
        self.support_channel = _make_channel(
            self.organization, code="foxray-support", name="FoxRay — поддержка",
            department=self.support, product=self.product,
        )
        self.orphan = _make_channel(self.organization, code="edevs", name="Edevs — сайт")

        user = HumanUser.objects.create_user(
            email="sales.lead@edevs.tech", password="Operator-Local-2026"
        )
        self.employee = OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Руководитель продаж",
            primary_department=self.sales,
        )
        profile = AccessProfile.objects.create(
            organization=self.organization, name="Channel manager"
        )
        for code in ("channels.view", "channels.manage"):
            AccessProfileCapability.objects.create(
                access_profile=profile, capability_code=code
            )
        owner = self.organization.memberships.get(role=EmployeeRole.OWNER)
        EmployeeAccessAssignment.objects.create(
            employee=self.employee,
            access_profile=profile,
            scope_type=ScopeType.DEPARTMENT,
            department=self.sales,
            assigned_by=owner,
        )
        self.scoped = APIClient()
        self.scoped.login(
            username="sales.lead@edevs.tech", password="Operator-Local-2026"
        )

    def test_list_hides_other_departments_and_orphan_channels(self) -> None:
        response = self.scoped.get("/api/v1/channels/")

        codes = {item["code"] for item in response.json()["items"]}
        self.assertEqual(codes, {"foxray-sales"})

    def test_channel_outside_scope_is_not_found(self) -> None:
        for channel in (self.support_channel, self.orphan):
            with self.subTest(code=channel.code):
                response = self.scoped.get(f"/api/v1/channels/{channel.id}/")
                self.assertEqual(response.status_code, 404)

    def test_scoped_manager_renames_own_channel(self) -> None:
        response = self.scoped.patch(
            f"/api/v1/channels/{self.sales_channel.id}/",
            data=json.dumps({"name": "FoxRay — продажи RU"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_scoped_manager_cannot_change_product_policy_or_status(self) -> None:
        for body in (
            {"productId": None},
            {"isActive": False},
            {"policy": {"allowCheckoutActions": True}},
        ):
            with self.subTest(body=body):
                response = self.scoped.patch(
                    f"/api/v1/channels/{self.sales_channel.id}/",
                    data=json.dumps(body),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 403)
        self.sales_channel.refresh_from_db()
        self.assertEqual(self.sales_channel.product_id, self.product.id)
        self.assertTrue(self.sales_channel.is_active)

    def test_scoped_manager_cannot_detach_department(self) -> None:
        # Снятие отдела вывело бы канал из собственной видимости сотрудника.
        response = self.scoped.patch(
            f"/api/v1/channels/{self.sales_channel.id}/",
            data=json.dumps({"departmentId": None}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.sales_channel.refresh_from_db()
        self.assertEqual(self.sales_channel.department_id, self.sales.id)

    def test_scoped_manager_cannot_move_channel_to_foreign_department(self) -> None:
        response = self.scoped.patch(
            f"/api/v1/channels/{self.sales_channel.id}/",
            data=json.dumps({"departmentId": self.support.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_scoped_manager_cannot_create_or_delete(self) -> None:
        created = self.scoped.post(
            "/api/v1/channels/",
            data=json.dumps(
                {
                    "code": "new-line",
                    "name": "Новая линия",
                    "departmentId": self.sales.id,
                    "policy": OPERATOR_POLICY,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 403)

        deleted = self.scoped.delete(f"/api/v1/channels/{self.sales_channel.id}/")
        self.assertEqual(deleted.status_code, 403)


class ChannelPermissionTests(ChannelApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = _make_channel(
            self.organization, code="firepage-sales", name="FirePage — продажи"
        )
        operator = HumanUser.objects.create_user(
            email="operator@edevs.tech", password="operator-password"
        )
        OrganizationMembership.objects.create(
            user=operator,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор",
            primary_department=None,
        )
        self.operator_client = APIClient()
        self.operator_client.login(
            username="operator@edevs.tech", password="operator-password"
        )

    def test_operator_without_capabilities_is_denied(self) -> None:
        self.assertEqual(self.operator_client.get("/api/v1/channels/").status_code, 403)
        response = self.operator_client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"name": "Взлом"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class ChannelCountersTests(ChannelApiTestCase):
    def test_returns_connection_breakdown_for_period(self) -> None:
        channel = _make_channel(self.organization, code="main", name="Основной")
        _messenger(self.organization, channel=channel)

        response = self.client.get(f"/api/v1/channels/{channel.id}/counters/?period=7d")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["period"], "7d")
        self.assertEqual(body["conversations"], {"open": 0, "total": 0})
        self.assertEqual(body["connections"], {"total": 1, "ok": 0, "error": 0})

    def test_rejects_unknown_period(self) -> None:
        channel = _make_channel(self.organization, code="main", name="Основной")
        response = self.client.get(f"/api/v1/channels/{channel.id}/counters/?period=1y")
        self.assertEqual(response.status_code, 400)
