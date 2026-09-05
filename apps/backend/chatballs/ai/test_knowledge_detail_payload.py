import json

from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.identity.bootstrap import bootstrap_edevs_owner
from chatballs.identity.models import Organization


class KnowledgeDetailPayloadTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")
        organization = Organization.objects.get(slug="edevs")
        self.base = f"/api/v1/organizations/{organization.public_id}/ai/knowledge"

    def test_detail_exposes_baseline_information_without_expanding_list_payload(self) -> None:
        created = self.client.post(
            f"{self.base}/",
            data=json.dumps({"title": "FAQ", "content": "Политика возврата"}),
            content_type="application/json",
        )
        knowledge_id = created.json()["knowledge"]["id"]

        detail = self.client.get(f"{self.base}/{knowledge_id}/").json()["knowledge"]
        listed = self.client.get(f"{self.base}/").json()["items"][0]

        self.assertTrue(detail["createdBy"])
        self.assertGreater(detail["fragmentsCount"], 0)
        self.assertNotIn("createdBy", listed)
