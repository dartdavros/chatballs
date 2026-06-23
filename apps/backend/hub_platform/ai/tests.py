import json

from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.ai.models import AIAgent
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser, Organization
from hub_platform.products.models import Product


class AIAgentInvariantTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")

    def test_each_product_has_exactly_one_agent(self) -> None:
        product_codes = set(Product.objects.values_list("code", flat=True))
        agent_codes = set(AIAgent.objects.values_list("product__code", flat=True))
        self.assertEqual(agent_codes, product_codes)
        self.assertEqual(AIAgent.objects.count(), Product.objects.count())

    def test_new_product_gets_an_agent(self) -> None:
        org = Organization.objects.get(slug="edevs")
        product = Product.objects.create(organization=org, code="academy", name="Academy")
        self.assertTrue(AIAgent.objects.filter(product=product).exists())


class AIAgentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_lists_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")

        self.assertEqual(response.status_code, 200)
        codes = {item["product"]["code"] for item in response.json()["items"]}
        self.assertEqual(codes, {"firepage", "foxray"})

    def test_owner_updates_agent_model(self) -> None:
        agent = AIAgent.objects.get(product__code="firepage")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"model": "anthropic/claude-3.5", "modelParams": {"temperature": 0.3}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        agent.refresh_from_db()
        self.assertEqual(agent.model, "anthropic/claude-3.5")
        self.assertEqual(agent.model_params, {"temperature": 0.3})

    def test_owner_deactivates_and_activates_agent(self) -> None:
        agent = AIAgent.objects.get(product__code="foxray")

        deactivated = self.client.post(f"/api/v1/ai/agents/{agent.id}/deactivate/")
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()["agent"]["isActive"])

        activated = self.client.post(f"/api/v1/ai/agents/{agent.id}/activate/")
        self.assertTrue(activated.json()["agent"]["isActive"])

    def test_update_rejects_invalid_model_params(self) -> None:
        agent = AIAgent.objects.get(product__code="firepage")

        response = self.client.patch(
            f"/api/v1/ai/agents/{agent.id}/update/",
            data=json.dumps({"modelParams": "not-an-object"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


class AIAgentPermissionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=Organization.objects.get(slug="edevs"),
            role=EmployeeRole.OPERATOR,
            department=None,
        )
        self.client = APIClient()
        self.client.login(username="operator@edevs.tech", password="operator-password")

    def test_operator_cannot_access_agents(self) -> None:
        response = self.client.get("/api/v1/ai/agents/")
        self.assertEqual(response.status_code, 403)

    def test_operator_cannot_access_knowledge(self) -> None:
        response = self.client.get("/api/v1/ai/knowledge/")
        self.assertEqual(response.status_code, 403)


class KnowledgeDocumentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def _create(self, **overrides):
        payload = {"product": "firepage", "code": "faq", "title": "FAQ", "category": "FAQ", "content": "v1"}
        payload.update(overrides)
        return self.client.post("/api/v1/ai/knowledge/", data=json.dumps(payload), content_type="application/json")

    def test_create_makes_first_draft_version(self) -> None:
        response = self._create()

        self.assertEqual(response.status_code, 201)
        document = response.json()["document"]
        self.assertEqual(document["category"], "FAQ")
        self.assertEqual(document["inclusionMode"], "RETRIEVAL")
        self.assertEqual(len(document["versions"]), 1)
        self.assertEqual(document["versions"][0]["status"], "DRAFT")
        self.assertEqual(document["versions"][0]["content"], "v1")

    def test_add_version_then_publish_archives_previous(self) -> None:
        document_id = self._create().json()["document"]["id"]
        self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/versions/",
            data=json.dumps({"content": "v2"}),
            content_type="application/json",
        )
        self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/1/publish/")
        response = self.client.post(f"/api/v1/ai/knowledge/{document_id}/versions/2/publish/")

        self.assertEqual(response.status_code, 200)
        versions = {v["version"]: v["status"] for v in response.json()["document"]["versions"]}
        self.assertEqual(versions[2], "PUBLISHED")
        self.assertEqual(versions[1], "ARCHIVED")

    def test_rollback_creates_new_draft_from_old_content(self) -> None:
        document_id = self._create().json()["document"]["id"]
        self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/versions/",
            data=json.dumps({"content": "v2"}),
            content_type="application/json",
        )
        response = self.client.post(
            f"/api/v1/ai/knowledge/{document_id}/rollback/",
            data=json.dumps({"version": 1}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        versions = response.json()["document"]["versions"]
        latest = max(versions, key=lambda v: v["version"])
        self.assertEqual(latest["version"], 3)
        self.assertEqual(latest["status"], "DRAFT")
        self.assertEqual(latest["content"], "v1")

    def test_create_rejects_unknown_category(self) -> None:
        self.assertEqual(self._create(category="NOPE").status_code, 400)

    def test_disable_and_enable(self) -> None:
        document_id = self._create().json()["document"]["id"]
        disabled = self.client.post(f"/api/v1/ai/knowledge/{document_id}/disable/")
        self.assertFalse(disabled.json()["document"]["isEnabled"])
        enabled = self.client.post(f"/api/v1/ai/knowledge/{document_id}/enable/")
        self.assertTrue(enabled.json()["document"]["isEnabled"])

    def test_create_for_foreign_product_is_rejected(self) -> None:
        Organization.objects.create(name="Other", slug="other")
        # product code resolved within the owner's organization only
        response = self._create(product="missing")
        self.assertEqual(response.status_code, 400)


class PromptDocumentApiTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_create_prompt_without_inclusion_mode(self) -> None:
        response = self.client.post(
            "/api/v1/ai/prompts/",
            data=json.dumps({"product": "foxray", "code": "system", "title": "System", "category": "SYSTEM", "content": "be helpful"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        document = response.json()["document"]
        self.assertEqual(document["category"], "SYSTEM")
        self.assertNotIn("inclusionMode", document)
        self.assertEqual(document["versions"][0]["content"], "be helpful")

    def test_prompt_rejects_knowledge_category(self) -> None:
        response = self.client.post(
            "/api/v1/ai/prompts/",
            data=json.dumps({"product": "foxray", "code": "x", "title": "X", "category": "FAQ", "content": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
