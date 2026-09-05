import json

from chatballs.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from chatballs.ai.models import KnowledgeCategory
from chatballs.testing import TenantAPIClient


class KnowledgeCategoryApiTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.admin.user)

    def _create(
        self, name: str, *, parent_id: int | None = None, sort_order: int = 0
    ):
        payload = {"name": name, "sortOrder": sort_order}
        if parent_id is not None:
            payload["parentId"] = parent_id
        return self.client.post(
            "/api/v1/ai/knowledge/categories/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_tree_is_preordered_and_counts_only_authorized_knowledge(self) -> None:
        child = self._create("Child", parent_id=self.products.id).json()["category"]

        response = self.client.get("/api/v1/ai/knowledge/categories/")

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        ids = [item["id"] for item in items]
        self.assertLess(ids.index(self.products.id), ids.index(child["id"]))
        products = next(item for item in items if item["id"] == self.products.id)
        self.assertEqual(products["knowledgeCount"], 4)

        self.client.force_authenticate(self.employee.user)
        restricted = self.client.get("/api/v1/ai/knowledge/categories/")
        self.assertEqual(restricted.status_code, 403)
        denied = self._create("Forbidden")
        self.assertEqual(denied.status_code, 403)

    def test_create_update_move_reorder_and_cycle_validation(self) -> None:
        root = self._create("Root", sort_order=10)
        self.assertEqual(root.status_code, 201)
        root_id = root.json()["category"]["id"]
        child_id = self._create("Child", parent_id=root_id).json()["category"]["id"]

        updated = self.client.patch(
            f"/api/v1/ai/knowledge/categories/{child_id}/",
            data=json.dumps(
                {"name": "Renamed", "parentId": None, "sortOrder": 25}
            ),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["category"]["name"], "Renamed")
        self.assertIsNone(updated.json()["category"]["parentId"])
        self.assertEqual(updated.json()["category"]["sortOrder"], 25)

        self.client.patch(
            f"/api/v1/ai/knowledge/categories/{child_id}/",
            data=json.dumps({"parentId": root_id}),
            content_type="application/json",
        )
        cycle = self.client.patch(
            f"/api/v1/ai/knowledge/categories/{root_id}/",
            data=json.dumps({"parentId": child_id}),
            content_type="application/json",
        )
        self.assertEqual(cycle.status_code, 400)
        self.assertIsNone(KnowledgeCategory.objects.get(id=root_id).parent_id)

    def test_delete_is_limited_to_empty_non_system_leaf(self) -> None:
        empty_id = self._create("Empty").json()["category"]["id"]
        deleted = self.client.delete(
            f"/api/v1/ai/knowledge/categories/{empty_id}/"
        )
        self.assertEqual(deleted.status_code, 204)

        nonempty = self.client.delete(
            f"/api/v1/ai/knowledge/categories/{self.products.id}/"
        )
        self.assertEqual(nonempty.status_code, 400)
        system = KnowledgeCategory.objects.get(
            organization=self.organization, is_system=True
        )
        protected = self.client.delete(
            f"/api/v1/ai/knowledge/categories/{system.id}/"
        )
        self.assertEqual(protected.status_code, 400)

        other_parent = KnowledgeCategory.objects.get(
            organization=self.other_organization, is_system=True
        )
        cross_tenant = self.client.post(
            "/api/v1/ai/knowledge/categories/",
            data=json.dumps({"name": "Invalid", "parentId": other_parent.id}),
            content_type="application/json",
        )
        self.assertEqual(cross_tenant.status_code, 400)
