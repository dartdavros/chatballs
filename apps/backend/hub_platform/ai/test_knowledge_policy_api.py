import json

from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.models import AIAgent
from hub_platform.channels.models import Channel
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.testing import TenantAPIClient


class KnowledgePolicyApiTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        create_test_subscription(self.organization)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.sales_employee.user)

    def test_list_detail_and_filters_do_not_disclose_other_department(self) -> None:
        response = self.client.get("/api/v1/ai/knowledge/?search=support")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {self.multi_department.id},
        )
        hidden = self.client.get(
            f"/api/v1/ai/knowledge/{self.support_only.id}/"
        )
        self.assertEqual(hidden.status_code, 404)

    def test_mutations_require_complete_write_coverage(self) -> None:
        allowed = self.client.patch(
            f"/api/v1/ai/knowledge/{self.sales_only.id}/",
            data=json.dumps({"title": "Updated sales playbook"}),
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 200)

        for knowledge in (self.shared, self.support_only, self.multi_department):
            with self.subTest(knowledge_id=knowledge.id):
                denied = self.client.patch(
                    f"/api/v1/ai/knowledge/{knowledge.id}/",
                    data=json.dumps({"title": "Forbidden update"}),
                    content_type="application/json",
                )
                self.assertEqual(denied.status_code, 404)

        create = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps({"title": "Organization item"}),
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 403)

    def test_agent_endpoints_keep_channel_department_scope(self) -> None:
        sales_channel = Channel.objects.create(
            organization=self.organization,
            department=self.sales,
            code="api-sales-agent",
            name="Sales agent channel",
        )
        support_channel = Channel.objects.create(
            organization=self.organization,
            department=self.support,
            code="api-support-agent",
            name="Support agent channel",
        )
        sales_agent = AIAgent.objects.create(
            channel=sales_channel, name="Sales agent"
        )
        support_agent = AIAgent.objects.create(
            channel=support_channel, name="Support agent"
        )

        response = self.client.get("/api/v1/ai/agents/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["items"]],
            [sales_agent.id],
        )
        hidden = self.client.get(f"/api/v1/ai/agents/{support_agent.id}/")
        self.assertEqual(hidden.status_code, 404)
