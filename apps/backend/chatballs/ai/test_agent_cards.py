import json

from django.test import TestCase
from chatballs.testing import TenantAPIClient as APIClient

from chatballs.ai.models import AIAgent, AIAgentStatus
from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)


class AgentCardTestCase(TestCase):
    """Единая сущность «Агент» = канал + AI-конфигурация (ADR-HUB-0041 §4)."""

    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = Organization.objects.get(slug="demo")
        self.operators = self.organization.employee_groups.get(name="Операторы")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")

    def create_agent(self, name: str = "Приёмная", group_id: int | None = None):
        return self.client.post(
            "/api/v1/agents/",
            data=json.dumps({"name": name, "groupId": group_id}),
            content_type="application/json",
        )


class AgentCardCreateTests(AgentCardTestCase):
    def test_one_step_wizard_creates_channel_and_draft_agent(self) -> None:
        response = self.create_agent(group_id=self.operators.id)

        self.assertEqual(response.status_code, 201)
        card = response.json()["agent"]
        self.assertEqual(card["name"], "Приёмная")
        self.assertEqual(card["groupId"], self.operators.id)
        self.assertEqual(card["aiStatus"], AIAgentStatus.DRAFT)
        self.assertTrue(card["isActive"])
        self.assertEqual(card["connections"], [])
        channel = Channel.objects.get(id=card["id"])
        self.assertEqual(channel.ai_agent.id, card["aiAgentId"])
        self.assertEqual(channel.ai_agent.name, "Приёмная")

    def test_codes_are_generated_and_unique(self) -> None:
        first = self.create_agent(name="Support line")
        second = self.create_agent(name="Support line!")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        codes = {first.json()["agent"]["code"], second.json()["agent"]["code"]}
        self.assertEqual(codes, {"support-line", "support-line-2"})

    def test_cyrillic_name_gets_fallback_code(self) -> None:
        response = self.create_agent(name="Продажи")
        self.assertEqual(response.json()["agent"]["code"], "agent")

    def test_empty_name_is_rejected(self) -> None:
        response = self.create_agent(name="   ")
        self.assertEqual(response.status_code, 400)

    def test_foreign_group_is_rejected(self) -> None:
        from chatballs.identity.group_models import EmployeeGroup

        other = Organization.objects.create(slug="other-cards", name="Other")
        foreign = EmployeeGroup.objects.create(organization=other, name="Чужая")
        response = self.create_agent(group_id=foreign.id)
        self.assertEqual(response.status_code, 400)


class AgentCardListDetailTests(AgentCardTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.card_id = self.create_agent(group_id=self.operators.id).json()["agent"]["id"]

    def test_list_returns_cards_with_group_filter(self) -> None:
        self.create_agent(name="Без группы")
        listed = self.client.get("/api/v1/agents/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["items"]), 2)

        grouped = self.client.get(f"/api/v1/agents/?group={self.operators.id}")
        self.assertEqual(
            [item["id"] for item in grouped.json()["items"]], [self.card_id]
        )
        ungrouped = self.client.get("/api/v1/agents/?group=none")
        self.assertEqual(
            [item["name"] for item in ungrouped.json()["items"]], ["Без группы"]
        )

    def test_legacy_channel_without_agent_gets_draft_agent_in_list(self) -> None:
        channel = Channel.objects.create(
            organization=self.organization, code="legacy", name="Legacy"
        )
        response = self.client.get(f"/api/v1/agents/{channel.id}/")
        self.assertEqual(response.status_code, 200)
        card = response.json()["agent"]
        self.assertEqual(card["aiStatus"], AIAgentStatus.DRAFT)
        self.assertTrue(AIAgent.objects.filter(channel=channel).exists())

    def test_employee_is_denied(self) -> None:
        user = HumanUser.objects.create_user(
            email="employee@example.com", password="employee-password"
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор",
        )
        client = APIClient()
        client.login(username="employee@example.com", password="employee-password")
        self.assertEqual(client.get("/api/v1/agents/").status_code, 403)

    def test_other_organization_card_is_not_found(self) -> None:
        other = Organization.objects.create(slug="other-detail", name="Other")
        foreign = Channel.objects.create(organization=other, code="f", name="F")
        response = self.client.get(f"/api/v1/agents/{foreign.id}/")
        self.assertEqual(response.status_code, 404)


class AgentCardUpdateTests(AgentCardTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.card = self.create_agent(group_id=self.operators.id).json()["agent"]

    def patch(self, **body):
        return self.client.patch(
            f"/api/v1/agents/{self.card['id']}/",
            data=json.dumps(body),
            content_type="application/json",
        )

    def test_rename_updates_channel_and_agent_together(self) -> None:
        response = self.patch(name="Новая приёмная")
        self.assertEqual(response.status_code, 200)
        card = response.json()["agent"]
        self.assertEqual(card["name"], "Новая приёмная")
        agent = AIAgent.objects.get(id=card["aiAgentId"])
        self.assertEqual(agent.name, "Новая приёмная")
        # Код неизменен: он входит в embed-URL виджета.
        self.assertEqual(card["code"], self.card["code"])

    def test_moves_between_groups_and_detaches(self) -> None:
        support = self.organization.employee_groups.get(name="Поддержка")
        moved = self.patch(groupId=support.id)
        self.assertEqual(moved.json()["agent"]["groupId"], support.id)
        detached = self.patch(groupId=None)
        self.assertIsNone(detached.json()["agent"]["groupId"])

    def test_updates_instructions_without_touching_channel(self) -> None:
        response = self.patch(persona="Помощник", instructions="Отвечай кратко")
        card = response.json()["agent"]
        self.assertEqual(card["persona"], "Помощник")
        self.assertEqual(card["instructions"], "Отвечай кратко")
        self.assertEqual(card["name"], self.card["name"])

    def test_deactivates_channel(self) -> None:
        response = self.patch(isActive=False)
        self.assertFalse(response.json()["agent"]["isActive"])

    def test_unknown_knowledge_id_rejects_whole_patch(self) -> None:
        response = self.patch(persona="X", knowledgeIds=[999999])
        self.assertEqual(response.status_code, 400)
        agent = AIAgent.objects.get(id=self.card["aiAgentId"])
        self.assertEqual(agent.persona, "")

    def test_knowledge_selection_semantics(self) -> None:
        # Пустой список снимает выбор; отсутствие ключа — не трогает.
        from chatballs.ai.knowledge_categories import ensure_uncategorized_category
        from chatballs.ai.models import Knowledge

        knowledge = Knowledge.objects.create(
            organization=self.organization,
            category=ensure_uncategorized_category(self.organization),
            title="FAQ",
            content="v1",
        )
        agent = AIAgent.objects.get(id=self.card["aiAgentId"])

        self.assertEqual(self.patch(knowledgeIds=[knowledge.id]).status_code, 200)
        self.assertEqual(agent.knowledge_items.count(), 1)
        self.patch(name="Renamed")
        self.assertEqual(agent.knowledge_items.count(), 1)
        self.patch(knowledgeIds=[])
        self.assertEqual(agent.knowledge_items.count(), 0)


class AgentCardActivationTests(AgentCardTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.card = self.create_agent().json()["agent"]

    def _byok_integration(self) -> Integration:
        from chatballs.integrations.models import IntegrationProvider
        from chatballs.integrations.services import IntegrationInput, create_integration
        from chatballs.testing import system_tenant_context

        return create_integration(
            context=system_tenant_context(self.organization),
            data=IntegrationInput(
                provider=IntegrationProvider.OPENROUTER,
                name="BYOK",
                secret="sk-byok",
                config={"baseUrl": "https://openrouter.ai/api/v1", "defaultModel": "byok-model"},
            ),
        )

    def test_activation_without_provider_integration_is_rejected(self) -> None:
        # Активация требует выбранного провайдера организации (ADR-HUB-0042 §2);
        # деактивация свободна.
        response = self.client.post(f"/api/v1/agents/{self.card['id']}/activate/")

        self.assertEqual(response.status_code, 400)
        self.assertIn("провайдера", response.json()["detail"])
        agent = AIAgent.objects.get(id=self.card["aiAgentId"])
        self.assertNotEqual(agent.status, AIAgentStatus.ACTIVE)

    def test_activates_and_deactivates_with_provider(self) -> None:
        integration = self._byok_integration()
        patched = self.client.patch(
            f"/api/v1/agents/{self.card['id']}/",
            data=json.dumps({"providerIntegrationId": integration.id}),
            content_type="application/json",
        )
        self.assertEqual(patched.status_code, 200)
        # Модель принадлежит интеграции: агент получает её default_model.
        self.assertEqual(patched.json()["agent"]["model"], "byok-model")

        activated = self.client.post(f"/api/v1/agents/{self.card['id']}/activate/")
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.json()["agent"]["aiStatus"], AIAgentStatus.ACTIVE)

        deactivated = self.client.post(f"/api/v1/agents/{self.card['id']}/deactivate/")
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(deactivated.json()["agent"]["aiStatus"], AIAgentStatus.DISABLED)


class AgentCardDeleteTests(AgentCardTestCase):
    def test_deletes_card_with_agent(self) -> None:
        card = self.create_agent().json()["agent"]
        response = self.client.delete(f"/api/v1/agents/{card['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Channel.objects.filter(id=card["id"]).exists())
        self.assertFalse(AIAgent.objects.filter(id=card["aiAgentId"]).exists())

    def test_connections_block_deletion(self) -> None:
        card = self.create_agent().json()["agent"]
        Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Bot",
            channel_id=card["id"],
        )
        response = self.client.delete(f"/api/v1/agents/{card['id']}/")
        self.assertEqual(response.status_code, 409)
        blockers = {item["type"] for item in response.json()["blockers"]}
        self.assertEqual(blockers, {"connections"})
        self.assertTrue(Channel.objects.filter(id=card["id"]).exists())


class AgentCardConnectionTests(AgentCardTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.card = self.create_agent().json()["agent"]
        self.integration = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.TELEGRAM,
            name="Telegram Bot",
        )

    def test_binds_and_unbinds_connection_from_card(self) -> None:
        bound = self.client.post(
            f"/api/v1/agents/{self.card['id']}/connections/",
            data=json.dumps({"integrationId": self.integration.id}),
            content_type="application/json",
        )
        self.assertEqual(bound.status_code, 200)
        self.assertEqual(len(bound.json()["agent"]["connections"]), 1)

        unbound = self.client.delete(
            f"/api/v1/agents/{self.card['id']}/connections/{self.integration.id}/"
        )
        self.assertEqual(unbound.status_code, 200)
        self.assertEqual(unbound.json()["agent"]["connections"], [])
        self.integration.refresh_from_db()
        self.assertIsNone(self.integration.channel_id)

    def test_move_between_agents_requires_force(self) -> None:
        other = self.create_agent(name="Вторая линия").json()["agent"]
        self.client.post(
            f"/api/v1/agents/{self.card['id']}/connections/",
            data=json.dumps({"integrationId": self.integration.id}),
            content_type="application/json",
        )
        conflict = self.client.post(
            f"/api/v1/agents/{other['id']}/connections/",
            data=json.dumps({"integrationId": self.integration.id}),
            content_type="application/json",
        )
        self.assertEqual(conflict.status_code, 409)
        forced = self.client.post(
            f"/api/v1/agents/{other['id']}/connections/",
            data=json.dumps({"integrationId": self.integration.id, "force": True}),
            content_type="application/json",
        )
        self.assertEqual(forced.status_code, 200)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.channel_id, other["id"])
