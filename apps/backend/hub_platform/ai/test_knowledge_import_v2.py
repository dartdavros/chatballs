import json

from django.test import TestCase

from hub_platform.ai.knowledge_categories import create_category
from hub_platform.ai.knowledge_policy_test_base import KnowledgePolicyTestBase
from hub_platform.ai.knowledge_types import UNCATEGORIZED_CATEGORY_NAME
from hub_platform.ai.models import AIAgent, AIAgentStatus, Knowledge, KnowledgeCategory
from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.testing import TenantAPIClient, system_tenant_context


class KnowledgeMetadataImportTests(TestCase):
    def setUp(self) -> None:
        result = bootstrap_edevs_owner(
            email="owner@edevs.tech",
            password="temporary-password",
        )
        self.organization = result.organization
        self.context = system_tenant_context(self.organization)
        self.products = create_category(
            context=self.context,
            name="Products",
        )
        self.foxray = create_category(
            context=self.context,
            name="FoxRay",
            parent=self.products,
        )
        self.client = TenantAPIClient()
        self.client.login(
            username="owner@edevs.tech",
            password="temporary-password",
        )

    def _import(self, documents: list[object]):
        return self.client.post(
            "/api/v1/ai/knowledge/import/",
            data=json.dumps({"documents": documents}),
            content_type="application/json",
        )

    def test_legacy_document_uses_uncategorized_default(self) -> None:
        response = self._import([{"title": "Legacy", "content": "Legacy text"}])

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created"], 1)
        knowledge = Knowledge.objects.get(title="Legacy")
        self.assertEqual(knowledge.category.name, UNCATEGORIZED_CATEGORY_NAME)

    def test_explicit_category_path_is_imported(self) -> None:
        response = self._import(
            [
                {
                    "title": "FoxRay support",
                    "description": "Support rules",
                    "categoryPath": ["Products", "FoxRay"],
                    "content": "Procedure",
                }
            ]
        )

        self.assertEqual(response.json()["created"], 1)
        knowledge = Knowledge.objects.get(title="FoxRay support")
        self.assertEqual(knowledge.category_id, self.foxray.id)

    def test_unknown_category_path_fails_per_document(self) -> None:
        response = self._import(
            [
                {
                    "title": "Unknown path",
                    "categoryPath": ["Products", "Missing"],
                    "content": "No",
                },
                {"title": "Valid", "content": "Yes"},
            ]
        )

        payload = response.json()
        self.assertEqual(payload["created"], 1)
        self.assertEqual(len(payload["failed"]), 1)
        self.assertFalse(Knowledge.objects.filter(title="Unknown path").exists())
        self.assertFalse(
            KnowledgeCategory.objects.filter(
                organization=self.organization,
                name="Missing",
            ).exists()
        )

    def test_omitted_metadata_preserves_category_and_agent_links(self) -> None:
        self._import(
            [
                {
                    "title": "Preserved",
                    "categoryPath": ["Products", "FoxRay"],
                    "content": "Version one",
                }
            ]
        )
        knowledge = Knowledge.objects.get(title="Preserved")
        channel = Channel.objects.create(
            organization=self.organization,
            code="import-support",
            name="Import support",
        )
        agent = AIAgent.objects.create(
            channel=channel,
            name="Import agent",
            status=AIAgentStatus.ACTIVE,
        )
        agent.knowledge_items.add(knowledge)

        response = self._import([{"title": "Preserved", "content": "Version two"}])

        self.assertEqual(response.json()["updated"], 1)
        knowledge.refresh_from_db()
        self.assertEqual(knowledge.category_id, self.foxray.id)
        self.assertTrue(agent.knowledge_items.filter(id=knowledge.id).exists())

    def test_metadata_only_update_keeps_existing_fragments(self) -> None:
        self._import([{"title": "Metadata", "content": "Stable content"}])
        knowledge = Knowledge.objects.get(title="Metadata")
        fragment_ids = list(knowledge.fragments.values_list("id", flat=True))

        response = self._import(
            [
                {
                    "title": "Metadata",
                    "categoryPath": ["Products", "FoxRay"],
                    "content": "Stable content",
                }
            ]
        )

        self.assertEqual(response.json()["updated"], 1)
        knowledge.refresh_from_db()
        self.assertEqual(knowledge.category_id, self.foxray.id)
        self.assertEqual(
            list(knowledge.fragments.values_list("id", flat=True)),
            fragment_ids,
        )


class KnowledgeImportPolicyTests(KnowledgePolicyTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.client = TenantAPIClient()
        self.client.force_login(self.employee.user)

    def test_employee_cannot_import_knowledge(self) -> None:
        response = self.client.post(
            "/api/v1/ai/knowledge/import/",
            data=json.dumps(
                {
                    "documents": [
                        {
                            "title": self.support_only.title,
                            "content": "Attempted overwrite",
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.support_only.refresh_from_db()
        self.assertEqual(self.support_only.content, "")
