import json

from django.test import TestCase

from hub_platform.ai.knowledge_services import KnowledgeInput, create_knowledge
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.knowledge_visibility import replace_knowledge_visibility
from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.testing import TenantAPIClient, system_tenant_context


class KnowledgeScopeConflictTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.sales = result.sales_department
        self.support = result.support_department
        self.context = system_tenant_context(self.organization)
        self.sales_channel = Channel.objects.create(
            organization=self.organization,
            code="conflict-sales",
            name="Sales channel",
            department=self.sales,
        )
        self.support_channel = Channel.objects.create(
            organization=self.organization,
            code="conflict-support",
            name="Support channel",
            department=self.support,
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _knowledge(
        self,
        *,
        title: str = "Policy",
        visibility: str = KnowledgeVisibility.ORGANIZATION,
        department_ids: tuple[int, ...] = (),
    ):
        return create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title=title,
                description="",
                content="Policy text",
                is_enabled=True,
                visibility=visibility,
                department_ids=department_ids,
            ),
        )

    def _agent(
        self,
        channel: Channel,
        knowledge,
        *,
        name: str,
        status: str = AIAgentStatus.ACTIVE,
    ) -> AIAgent:
        agent = AIAgent.objects.create(
            channel=channel,
            name=name,
            status=status,
        )
        agent.knowledge_items.add(knowledge)
        return agent

    def test_visibility_change_returns_stable_conflicts_and_rolls_back(self) -> None:
        knowledge = self._knowledge()
        sales_agent = self._agent(
            self.sales_channel,
            knowledge,
            name="Sales agent",
        )
        self._agent(
            self.support_channel,
            knowledge,
            name="Support agent",
        )

        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "title": "Changed title",
                    "visibility": KnowledgeVisibility.DEPARTMENTS,
                    "departmentIds": [self.support.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["code"], "agent_knowledge_scope_conflict")
        self.assertEqual(
            payload["conflicts"],
            [
                {
                    "agent": {"id": sales_agent.id, "name": "Sales agent"},
                    "knowledge": {"id": knowledge.id, "title": "Policy"},
                }
            ],
        )
        knowledge.refresh_from_db()
        self.assertEqual(knowledge.title, "Policy")
        self.assertEqual(knowledge.visibility, KnowledgeVisibility.ORGANIZATION)
        self.assertFalse(knowledge.department_links.exists())

    def test_department_link_replacement_is_blocked_without_partial_change(
        self,
    ) -> None:
        knowledge = self._knowledge(
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=(self.sales.id, self.support.id),
        )
        self._agent(self.sales_channel, knowledge, name="Sales agent")

        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps({"departmentIds": [self.support.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        knowledge.refresh_from_db()
        self.assertEqual(
            set(knowledge.department_links.values_list("department_id", flat=True)),
            {self.sales.id, self.support.id},
        )

    def test_disabled_non_archived_agent_still_blocks_scope_change(self) -> None:
        knowledge = self._knowledge()
        self._agent(
            self.sales_channel,
            knowledge,
            name="Disabled sales agent",
            status=AIAgentStatus.DISABLED,
        )

        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "visibility": KnowledgeVisibility.DEPARTMENTS,
                    "departmentIds": [self.support.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)

    def test_archived_agent_does_not_block_scope_change(self) -> None:
        knowledge = self._knowledge()
        self._agent(
            self.sales_channel,
            knowledge,
            name="Archived sales agent",
            status=AIAgentStatus.ARCHIVED,
        )

        replace_knowledge_visibility(
            context=self.context,
            knowledge=knowledge,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=[self.support.id],
        )

        knowledge.refresh_from_db()
        self.assertEqual(knowledge.visibility, KnowledgeVisibility.DEPARTMENTS)
        self.assertEqual(
            list(knowledge.department_links.values_list("department_id", flat=True)),
            [self.support.id],
        )


class ChannelDepartmentConflictTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.sales = result.sales_department
        self.support = result.support_department
        self.context = system_tenant_context(self.organization)
        self.channel = Channel.objects.create(
            organization=self.organization,
            code="department-change",
            name="Original channel",
            department=self.sales,
        )
        self.knowledge = create_knowledge(
            context=self.context,
            data=KnowledgeInput(
                title="Sales only",
                description="",
                content="Sales procedure",
                is_enabled=True,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=(self.sales.id,),
            ),
        )
        self.agent = AIAgent.objects.create(
            channel=self.channel,
            name="Sales agent",
            status=AIAgentStatus.ACTIVE,
        )
        self.agent.knowledge_items.add(self.knowledge)
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def test_channel_department_change_is_blocked_and_atomic(self) -> None:
        response = self.client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"name": "Changed channel", "departmentId": self.support.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["conflicts"],
            [
                {
                    "agent": {"id": self.agent.id, "name": "Sales agent"},
                    "knowledge": {
                        "id": self.knowledge.id,
                        "title": "Sales only",
                    },
                }
            ],
        )
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "Original channel")
        self.assertEqual(self.channel.department_id, self.sales.id)

    def test_compatible_channel_department_change_succeeds(self) -> None:
        replace_knowledge_visibility(
            context=self.context,
            knowledge=self.knowledge,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=[self.sales.id, self.support.id],
        )

        response = self.client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"departmentId": self.support.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.department_id, self.support.id)
