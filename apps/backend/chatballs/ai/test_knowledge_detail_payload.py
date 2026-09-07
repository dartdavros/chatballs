import json

from django.test import TestCase
from rest_framework.test import APIClient

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import Organization


class KnowledgeDetailPayloadTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")
        organization = Organization.objects.get(slug="demo")
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
        # Автор последней правки стоит под датой в колонке «Обновлено»
        # (дизайн-базлайн v2, кадр KB1), поэтому он есть и в списке.
        self.assertEqual(listed["updatedBy"], detail["updatedBy"])
        self.assertTrue(listed["updatedBy"])


class KnowledgeReindexTests(TestCase):
    def setUp(self) -> None:
        bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = APIClient()
        self.client.login(username="owner@example.com", password="temporary-password")
        organization = Organization.objects.get(slug="demo")
        self.base = f"/api/v1/organizations/{organization.public_id}/ai/knowledge"

    def test_reindex_rebuilds_fragments_of_knowledge(self) -> None:
        created = self.client.post(
            f"{self.base}/",
            data=json.dumps({"title": "Сроки", "content": "Рубашка — 10 дней.\n\nПальто — 25 дней."}),
            content_type="application/json",
        )
        knowledge_id = created.json()["knowledge"]["id"]
        before = self.client.get(f"{self.base}/{knowledge_id}/").json()["knowledge"]["fragmentsCount"]

        response = self.client.post(f"{self.base}/{knowledge_id}/reindex/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["knowledge"]["fragmentsCount"], before)
        self.assertGreater(before, 0)
