import json

from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.testing import TenantAPIClient


class KnowledgeBulkPolicyTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        from hub_platform.subscriptions.testing import create_test_subscription

        create_test_subscription(self.organization)
        self.target = create_category(
            context=self.system_context,
            name="Bulk target",
        )
        self.client = TenantAPIClient()
        self.client.force_login(self.sales_employee.user)

    def _post(self, path: str, payload: dict[str, object]):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_mixed_scope_move_is_denied_and_atomic(self) -> None:
        response = self._post(
            "/api/v1/ai/knowledge/bulk/move/",
            {
                "knowledgeIds": [self.sales_only.id, self.support_only.id],
                "categoryId": self.target.id,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.sales_only.refresh_from_db()
        self.support_only.refresh_from_db()
        self.assertEqual(self.sales_only.category_id, self.products.id)
        self.assertEqual(self.support_only.category_id, self.products.id)

    def test_mixed_scope_visibility_change_is_denied_and_atomic(self) -> None:
        response = self._post(
            "/api/v1/ai/knowledge/bulk/visibility/",
            {
                "knowledgeIds": [self.sales_only.id, self.support_only.id],
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.sales.id],
            },
        )

        self.assertEqual(response.status_code, 403)
        self.sales_only.refresh_from_db()
        self.support_only.refresh_from_db()
        self.assertEqual(
            set(self.sales_only.departments.values_list("id", flat=True)),
            {self.sales.id},
        )
        self.assertEqual(
            set(self.support_only.departments.values_list("id", flat=True)),
            {self.support.id},
        )
