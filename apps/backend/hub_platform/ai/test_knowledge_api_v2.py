import json

from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.testing import TenantAPIClient


class HierarchicalKnowledgeApiTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        create_test_subscription(self.organization)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.admin.user)
        self.guides = create_category(
            context=self.system_context,
            parent=self.products,
            name="Guides",
        )

    def _post(self, payload: dict[str, object]):
        return self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_create_and_detail_return_category_payload(self) -> None:
        response = self._post(
            {
                "title": "Team guide",
                "description": "For everyone",
                "content": "Guide content",
                "categoryId": self.guides.id,
            }
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["knowledge"]
        self.assertEqual(
            payload["category"],
            {"id": self.guides.id, "name": "Guides", "parentId": self.products.id},
        )
        self.assertNotIn("visibility", payload)
        self.assertNotIn("departments", payload)
        detail = self.client.get(f"/api/v1/ai/knowledge/{payload['id']}/")
        self.assertEqual(detail.json()["knowledge"]["content"], "Guide content")

    def test_update_category_and_metadata_is_atomic(self) -> None:
        knowledge = self.sales_only
        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "title": "Moved playbook",
                    "category": {"id": self.guides.id},
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["knowledge"]
        self.assertEqual(payload["category"]["id"], self.guides.id)

        invalid = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "title": "Must roll back",
                    "categoryId": 999999,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        knowledge.refresh_from_db()
        self.assertEqual(knowledge.title, "Moved playbook")
        self.assertEqual(knowledge.category_id, self.guides.id)

    def test_list_filters_category_status_and_search(self) -> None:
        created = self._post(
            {
                "title": "Disabled filtered guide",
                "description": "Unique filter phrase",
                "categoryId": self.guides.id,
                "isEnabled": False,
            }
        ).json()["knowledge"]
        response = self.client.get(
            "/api/v1/ai/knowledge/",
            {
                "category": self.guides.id,
                "isEnabled": "false",
                "search": "unique filter",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["items"]], [created["id"]]
        )

        invalid = self.client.get("/api/v1/ai/knowledge/", {"isEnabled": "banana"})
        self.assertEqual(invalid.status_code, 400)
