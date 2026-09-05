import json

from chatballs.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from chatballs.ai.models import AIAgent
from chatballs.channels.models import Channel
from chatballs.testing import TenantAPIClient


class KnowledgePolicyApiTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.admin.user)

    def test_admin_sees_whole_library_and_employee_gets_403(self) -> None:
        response = self.client.get("/api/v1/ai/knowledge/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.json()["items"]},
            {
                self.shared.id,
                self.sales_only.id,
                self.support_only.id,
                self.disabled.id,
            },
        )
        detail = self.client.get(f"/api/v1/ai/knowledge/{self.support_only.id}/")
        self.assertEqual(detail.status_code, 200)

        self.client.force_authenticate(self.employee.user)
        self.assertEqual(self.client.get("/api/v1/ai/knowledge/").status_code, 403)
        self.assertEqual(
            self.client.get(
                f"/api/v1/ai/knowledge/{self.shared.id}/"
            ).status_code,
            403,
        )

    def test_admin_mutations_allowed_and_employee_denied(self) -> None:
        allowed = self.client.patch(
            f"/api/v1/ai/knowledge/{self.sales_only.id}/",
            data=json.dumps({"title": "Updated sales playbook"}),
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 200)

        created = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps({"title": "Organization item"}),
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)

        self.client.force_authenticate(self.employee.user)
        denied_patch = self.client.patch(
            f"/api/v1/ai/knowledge/{self.sales_only.id}/",
            data=json.dumps({"title": "Forbidden update"}),
            content_type="application/json",
        )
        self.assertEqual(denied_patch.status_code, 403)
        denied_create = self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps({"title": "Forbidden item"}),
            content_type="application/json",
        )
        self.assertEqual(denied_create.status_code, 403)

    def test_agent_endpoints_are_organization_wide_and_closed_for_employee(self) -> None:
        channel = Channel.objects.create(
            organization=self.organization,
            code="api-agent",
            name="Agent channel",
        )
        agent = AIAgent.objects.create(channel=channel, name="Agent")

        response = self.client.get("/api/v1/agents/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["aiAgentId"] for item in response.json()["items"]],
            [agent.id],
        )
        detail = self.client.get(f"/api/v1/agents/{channel.id}/")
        self.assertEqual(detail.status_code, 200)

        self.client.force_authenticate(self.employee.user)
        self.assertEqual(self.client.get("/api/v1/agents/").status_code, 403)
        self.assertEqual(
            self.client.get(f"/api/v1/agents/{channel.id}/").status_code, 403
        )
