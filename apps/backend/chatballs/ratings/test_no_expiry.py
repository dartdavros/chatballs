"""Real API, poll, directory and SQL checks for aged WEB credentials."""

from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.test import APIClient

from chatballs.events.models import OutboxEvent
from chatballs.ratings.credentials import credential_for, hash_credential
from chatballs.ratings.models import CustomerRating, RatingRequest
from chatballs.ratings.public_service import resolved_request
from chatballs.ratings.settings_service import update_settings
from chatballs.ratings.test_support import RatingTestBase
from chatballs.ratings.web_delivery import deliver_due_requests, session_requests
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.models import WebSession


class RatingNoExpiryTests(RatingTestBase):
    def aged_request(self, *, legacy=False, transport="WEB"):
        event = self.row(event_type="CLOSED", transport=transport)
        event.save()
        target = RatingRequest.objects.get(completion=event)
        target.sent_at = timezone.now() - timedelta(days=365)
        target.expires_at = target.sent_at + timedelta(days=7) if legacy else None
        target.credential_hash = hash_credential(credential_for(target))
        target.save(update_fields=["sent_at", "expires_at", "credential_hash"])
        return target

    def client_for(self, target):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential_for(target)}")
        return client

    def directory(self, target):
        with connection.cursor() as cursor:
            cursor.execute("SELECT resource_id FROM chatballs.rating_request_directory WHERE lookup_key=%s",
                           [target.credential_hash])
            return cursor.fetchall()

    def test_old_and_legacy_credentials_poll_read_submit_repeat_and_conflict(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy):
                target = self.aged_request(legacy=legacy)
                token = credential_for(target)
                self.assertEqual(deliver_due_requests(self.context), 0)
                poll = session_requests(self.session)
                self.assertEqual([item["credential"] for item in poll], [token])
                self.assertIsNone(poll[0]["expiresAt"])
                client = self.client_for(target)
                with tenant_atomic(self.context), connection.cursor() as cursor:
                    cursor.execute("SET LOCAL ROLE chatballs_runtime_app")
                    self.assertEqual(self.directory(target), [(target.pk,)])
                    question = client.get("/api/v1/ratings/")
                    self.assertEqual(question.status_code, 200)
                    self.assertIsNone(question.data["expiresAt"])
                    data = {"value": 5, "comment": "Old tab response"}
                    first = client.post("/api/v1/ratings/", data, format="json")
                    self.assertEqual(first.status_code, 201)
                    repeat = client.post("/api/v1/ratings/", data, format="json")
                    self.assertEqual(repeat.status_code, 200)
                    self.assertEqual(repeat.data, first.data)
                    self.assertEqual(client.post("/api/v1/ratings/", {"value": 4}, format="json").status_code, 409)
                    cursor.execute("SET LOCAL ROLE NONE")
                self.assertEqual(session_requests(self.session), [])
                self.assertEqual(client.get("/api/v1/ratings/").data["result"], first.data)
        self.assertEqual(CustomerRating.objects.count(), 2)
        self.assertEqual(OutboxEvent.objects.filter(event_type="ratings.received").count(), 2)

    def test_sql_accepts_old_web_but_rejects_unsent_cancelled_and_foreign(self):
        target = self.aged_request(legacy=True)
        CustomerRating.objects.create(organization=self.organization, request=target, value="4")
        unsent = self.scheduled()
        cancelled = self.aged_request()
        RatingRequest.objects.filter(pk=cancelled.pk).update(cancelled_at=timezone.now())
        for request, organization in ((unsent, self.organization), (cancelled, self.organization),
                                      (target, self.foreign)):
            with self.subTest(request=request.pk, organization=organization.pk):
                with self.assertRaises(DatabaseError), transaction.atomic():
                    CustomerRating.objects.bulk_create([
                        CustomerRating(organization=organization, request=request, value="5"),
                    ])
        self.assertEqual(self.directory(cancelled), [])
        with self.assertRaises(DatabaseError), transaction.atomic():
            RatingRequest.objects.filter(pk=cancelled.pk).update(cancelled_at=None)

    def test_cancellation_deletion_and_organization_binding_still_close_access(self):
        target = self.aged_request(legacy=True)
        client = self.client_for(target)
        with self.assertRaises(NotFound), resolved_request(
            credential_for(target), expected_organization_id=self.foreign.pk,
        ):
            self.fail("foreign organization resolved")
        update_settings(self.context, {"enabled": False})
        self.assertEqual(self.directory(target), [])
        for method in (client.get, client.post):
            self.assertEqual(method("/api/v1/ratings/").status_code, 404)
        update_settings(self.context, {"enabled": True})
        self.assertEqual(client.get("/api/v1/ratings/").status_code, 404)
        other = self.aged_request(legacy=True)
        other_client = self.client_for(other)
        self.conversation.delete()
        self.assertEqual(self.directory(other), [])
        self.assertEqual(other_client.get("/api/v1/ratings/").status_code, 404)
        self.assertEqual(other_client.post("/api/v1/ratings/", {"value": 5}, format="json").status_code, 404)

    def test_session_timeout_is_unchanged_and_issued_credential_does_not_need_session(self):
        target = self.aged_request()
        idle = timedelta(seconds=settings.CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS + 1)
        WebSession.objects.filter(pk=self.session.pk).update(last_seen_at=timezone.now() - idle)
        self.assertEqual(session_requests(self.session), [])
        self.assertEqual(self.client_for(target).get("/api/v1/ratings/").status_code, 200)

    def test_old_verifier_survives_secret_rotation_without_regeneration(self):
        target = self.aged_request(legacy=True)
        client = self.client_for(target)
        with override_settings(SECRET_KEY="rotated-test-secret"):
            self.assertEqual(session_requests(self.session), [])
            self.assertEqual(client.get("/api/v1/ratings/").status_code, 200)

    def test_other_transports_keep_finite_expiry_in_api_directory_and_sql(self):
        self.connection.provider = "TELEGRAM"
        self.connection.save(update_fields=["provider"])
        target = self.aged_request(legacy=True, transport="TELEGRAM")
        self.assertEqual(self.directory(target), [])
        self.assertEqual(session_requests(self.session), [])
        client = self.client_for(target)
        self.assertEqual(client.get("/api/v1/ratings/").status_code, 404)
        self.assertEqual(client.post("/api/v1/ratings/", {"value": 5}, format="json").status_code, 404)
        with self.assertRaises(DatabaseError), transaction.atomic():
            CustomerRating.objects.create(organization=self.organization, request=target, value="5")
        with self.assertRaises(DatabaseError), transaction.atomic():
            RatingRequest.objects.filter(pk=target.pk).update(expires_at=None)
