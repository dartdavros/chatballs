import json

from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import Knowledge
from hub_platform.identity.models import Department, DepartmentStatus
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.testing import TenantAPIClient


class HierarchicalKnowledgeApiTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        create_test_subscription(self.organization)
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.organization_manager.user)
        self.guides = create_category(
            context=self.system_context,
            parent=self.products,
            name="Guides",
        )
        self.disabled_department = Department.objects.create(
            organization=self.organization,
            code="disabled-api",
            name="Disabled",
            status=DepartmentStatus.DISABLED,
        )

    def _post(self, payload: dict[str, object]):
        return self.client.post(
            "/api/v1/ai/knowledge/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_create_and_detail_return_complete_scope_payload(self) -> None:
        response = self._post(
            {
                "title": "Scoped guide",
                "description": "For two teams",
                "content": "Guide content",
                "categoryId": self.guides.id,
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.support.id, self.sales.id],
            }
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["knowledge"]
        self.assertEqual(
            payload["category"],
            {"id": self.guides.id, "name": "Guides", "parentId": self.products.id},
        )
        self.assertEqual(payload["visibility"], KnowledgeVisibility.DEPARTMENTS)
        self.assertEqual(
            [department["id"] for department in payload["departments"]],
            [self.sales.id, self.support.id],
        )
        detail = self.client.get(f"/api/v1/ai/knowledge/{payload['id']}/")
        self.assertEqual(detail.json()["knowledge"]["content"], "Guide content")

    def test_update_scope_category_and_metadata_is_atomic(self) -> None:
        knowledge = self.sales_only
        response = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "title": "Moved playbook",
                    "category": {"id": self.guides.id},
                    "visibility": KnowledgeVisibility.DEPARTMENTS,
                    "departments": [{"id": self.sales.id}, {"id": self.support.id}],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["knowledge"]
        self.assertEqual(payload["category"]["id"], self.guides.id)
        self.assertEqual(
            {item["id"] for item in payload["departments"]},
            {self.sales.id, self.support.id},
        )

        invalid = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps(
                {
                    "title": "Must roll back",
                    "departmentIds": [self.disabled_department.id],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        knowledge.refresh_from_db()
        self.assertEqual(knowledge.title, "Moved playbook")
        self.assertEqual(
            set(knowledge.departments.values_list("id", flat=True)),
            {self.sales.id, self.support.id},
        )

        organization_scope = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge.id}/",
            data=json.dumps({"visibility": KnowledgeVisibility.ORGANIZATION}),
            content_type="application/json",
        )
        self.assertEqual(organization_scope.status_code, 200)
        self.assertEqual(
            organization_scope.json()["knowledge"]["departments"], []
        )

    def test_department_manager_can_create_own_scope_but_cannot_expand_it(self) -> None:
        self.client.force_authenticate(self.sales_employee.user)
        created = self._post(
            {
                "title": "Sales only API",
                "categoryId": self.guides.id,
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.sales.id],
            }
        )
        self.assertEqual(created.status_code, 201)
        knowledge_id = created.json()["knowledge"]["id"]

        denied = self.client.patch(
            f"/api/v1/ai/knowledge/{knowledge_id}/",
            data=json.dumps({"departmentIds": [self.sales.id, self.support.id]}),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(
            set(
                Knowledge.objects.get(id=knowledge_id).departments.values_list(
                    "id", flat=True
                )
            ),
            {self.sales.id},
        )

    def test_list_filters_category_department_visibility_and_status(self) -> None:
        created = self._post(
            {
                "title": "Disabled filtered guide",
                "description": "Unique filter phrase",
                "categoryId": self.guides.id,
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "departmentIds": [self.sales.id],
                "isEnabled": False,
            }
        ).json()["knowledge"]
        response = self.client.get(
            "/api/v1/ai/knowledge/",
            {
                "category": self.guides.id,
                "department": self.sales.id,
                "visibility": KnowledgeVisibility.DEPARTMENTS,
                "isEnabled": "false",
                "search": "unique filter",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["items"]], [created["id"]]
        )

        invalid = self.client.get(
            "/api/v1/ai/knowledge/", {"visibility": "PUBLIC"}
        )
        self.assertEqual(invalid.status_code, 400)
