from django.db import connection
from rest_framework.test import APIClient

from chatballs.events.models import OutboxEvent
from chatballs.ratings.credentials import credential_for, hash_credential
from chatballs.ratings.models import CustomerRating
from chatballs.ratings.test_support import RatingTestBase
from chatballs.ratings.web_delivery import deliver_due_requests


class RatingPublicTests(RatingTestBase):
    def setUp(self):
        super().setUp()
        self.target = self.scheduled()
        deliver_due_requests(self.context)
        self.target.refresh_from_db()
        self.token = credential_for(self.target)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_public_question_is_limited_and_credential_not_persisted(self):
        response = self.client.get("/api/v1/ratings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"text", "scale", "expiresAt", "commentMaxLength", "result", "presentation"})
        self.assertEqual(set(response.data["presentation"]), {"name", "accent", "siteUrl", "conversationDate", "language"})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.target.credential_hash, hash_credential(self.token))
        self.assertNotEqual(self.target.credential_hash, self.token)
        self.assertIsNone(self.target.expires_at)
        self.assertIsNone(response.data["expiresAt"])
        self.assertFalse(self.conversation.messages.filter(text__contains=self.token).exists())

    def test_repeated_identical_response_and_changed_response_conflict(self):
        data = {"value": 5, "comment": "Customer response"}
        first = self.client.post("/api/v1/ratings/", data, format="json")
        self.assertEqual(first.status_code, 201)
        repeat = self.client.post("/api/v1/ratings/", data, format="json")
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(first.data, repeat.data)
        for replacement in ({"value": 4, "comment": data["comment"]}, {"value": 5, "comment": "Other"}):
            self.assertEqual(self.client.post("/api/v1/ratings/", replacement, format="json").status_code, 409)
        self.assertEqual(CustomerRating.objects.count(), 1)
        self.assertEqual(OutboxEvent.objects.filter(event_type="ratings.received").count(), 1)
        event = OutboxEvent.objects.get(event_type="ratings.received")
        self.assertEqual(event.payload, {"ratingId": CustomerRating.objects.get().pk})

    def test_invalid_values_comments_and_direct_id_injection_rejected(self):
        for data in ({"value": True}, {"value": "5"}, {"value": 0}, {"value": 6},
                     {"value": 5, "comment": "x" * 2001}, {"value": 5, "comment": None},
                     {"value": 5, "requestId": self.foreign_conversation.pk}):
            with self.subTest(data=str(data)[:80]):
                self.assertEqual(self.client.post("/api/v1/ratings/", data, format="json").status_code, 400)
        self.assertFalse(CustomerRating.objects.exists())

    def test_maximum_comment_is_accepted_and_foreign_ids_cannot_select_a_request(self):
        response = self.client.post("/api/v1/ratings/", {"value": 1, "comment": "x" * 2000}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["value"], 1)
        self.assertEqual(len(response.data["comment"]), 2000)
        self.assertEqual(self.client.get(f"/api/v1/ratings/{self.target.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/webchat/messages/").status_code, 401)

    def test_missing_bad_and_deleted_credentials_rejected(self):
        for header in ("", "Bearer wrong", f"Bearer {self.target.pk}", f"Bearer {'0' * 64}"):
            self.client.credentials(HTTP_AUTHORIZATION=header)
            self.assertEqual(self.client.get("/api/v1/ratings/").status_code, 404)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.conversation.delete()
        self.assertEqual(self.client.get("/api/v1/ratings/").status_code, 404)

    def test_runtime_role_can_resolve_only_credential_scoped_question(self):
        from chatballs.tenancy.database import tenant_atomic

        with tenant_atomic(self.context), connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
            self.assertEqual(self.client.get("/api/v1/ratings/").status_code, 200)
            self.assertEqual(self.client.post("/api/v1/ratings/", {"value": 5}, format="json").status_code, 201)
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL ROLE NONE")

    def test_rate_limits_by_ip_and_credential(self):
        for index in range(10):
            response = self.client.get("/api/v1/ratings/", REMOTE_ADDR=f"192.0.2.{index + 1}")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/ratings/", REMOTE_ADDR="192.0.2.100").status_code, 429)
        self.client.credentials()
        from django.core.cache import cache
        cache.clear()
        for _ in range(60):
            self.assertEqual(self.client.get("/api/v1/ratings/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/ratings/").status_code, 429)
