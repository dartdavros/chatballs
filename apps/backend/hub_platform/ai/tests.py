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
