"""Upgrade legacy guards in the isolated PostgreSQL test transaction only."""

from datetime import timedelta
from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from rest_framework.test import APIClient

from chatballs.events.models import OutboxEvent
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.ratings.credentials import credential_for, hash_credential
from chatballs.ratings.models import CustomerRating, RatingRequest, RatingSettings
from chatballs.ratings.test_support import RatingTestBase
from chatballs.ratings.web_delivery import deliver_due_requests, session_requests
from chatballs.webchat.models import WebSession


class RatingExpiryMigrationTests(RatingTestBase):
    def install_legacy_schema(self):
        # No migration recorder edits or schema rollback of unrelated apps.
        # TestCase rolls all DDL/data back after this test.
        legacy = import_module("chatballs.ratings.migrations.0002_guards")
        sql = legacy.GUARDS.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION")
        sql = sql.replace("CREATE VIEW", "CREATE OR REPLACE VIEW")
        with connection.schema_editor(atomic=False) as editor:
            editor.execute("DROP TRIGGER rating_request_guard ON ratings_ratingrequest")
            editor.execute("DROP TRIGGER customer_rating_guard ON ratings_customerrating")
            editor.execute(sql)
            editor.execute("ALTER TABLE ratings_ratingrequest DROP CONSTRAINT rating_credential_lifecycle")
            editor.execute("""ALTER TABLE ratings_ratingrequest ADD CONSTRAINT rating_credential_lifecycle CHECK (
                (sent_at IS NULL AND credential_hash IS NULL AND expires_at IS NULL) OR
                (sent_at IS NOT NULL AND credential_hash IS NOT NULL AND expires_at IS NOT NULL))""")

    def legacy_request(self, *, days, cancelled=False, answered=False):
        target = self.scheduled()
        target.sent_at = timezone.now() - timedelta(days=days)
        target.expires_at = target.sent_at + timedelta(days=7)
        target.credential_hash = hash_credential(credential_for(target))
        target.save(update_fields=["sent_at", "expires_at", "credential_hash"])
        if answered:
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential_for(target)}")
            self.assertEqual(client.post("/api/v1/ratings/", {"value": 4}, format="json").status_code, 201)
        if cancelled:
            target.cancelled_at = timezone.now()
            target.save(update_fields=["cancelled_at"])
        return target

    def test_upgrade_preserves_all_rows_and_revives_only_uncancelled_credentials(self):
        self.install_legacy_schema()
        self.row(event_type="PUBLIC_REPLY").save()
        expired = self.legacy_request(days=365)
        active = self.legacy_request(days=1)
        answered = self.legacy_request(days=1, answered=True)
        cancelled = self.legacy_request(days=365, cancelled=True)
        pending = self.scheduled()
        models = (RatingRequest, CustomerRating, RatingSettings, OutboxEvent,
                  HumanUser, OrganizationMembership, WebSession)
        before = {model: list(model.objects.order_by("pk").values()) for model in models}
        with connection.cursor() as cursor:
            cursor.execute("SELECT resource_id FROM chatballs.rating_request_directory WHERE lookup_key=%s",
                           [expired.credential_hash])
            self.assertEqual(cursor.fetchall(), [])
            cursor.execute("SELECT relowner, relacl, reloptions FROM pg_class WHERE oid='chatballs.rating_request_directory'::regclass")
            directory_acl = cursor.fetchone()
        migration = import_module("chatballs.ratings.migrations.0003_web_requests_without_expiry").Migration
        state = MigrationExecutor(connection).loader.project_state([("ratings", "0002_guards")])
        # Production upgrades run after the data transaction commits. Flush the
        # deferred FK/tenant checks held by TestCase before changing constraints.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        with connection.schema_editor(atomic=False) as editor:
            migration("0003_web_requests_without_expiry", "ratings").apply(state, editor)
        for model, rows in before.items():
            self.assertEqual(list(model.objects.order_by("pk").values()), rows, model.__name__)
        with connection.cursor() as cursor:
            cursor.execute("SELECT relowner, relacl, reloptions FROM pg_class WHERE oid='chatballs.rating_request_directory'::regclass")
            self.assertEqual(cursor.fetchone(), directory_acl)
        self.assertEqual({item["credential"] for item in session_requests(self.session)},
                         {credential_for(expired), credential_for(active)})
        for target in (expired, active, answered, cancelled):
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential_for(target)}")
            question = client.get("/api/v1/ratings/")
            self.assertEqual(question.status_code, 404 if target == cancelled else 200)
            if target != cancelled:
                self.assertIsNone(question.data["expiresAt"])
            if target == answered:
                prior = question.data["result"]
                self.assertEqual(client.post("/api/v1/ratings/", {"value": 4}, format="json").data, prior)
                self.assertEqual(client.post("/api/v1/ratings/", {"value": 5}, format="json").status_code, 409)
        self.assertEqual(deliver_due_requests(self.context), 1)
        pending.refresh_from_db()
        self.assertIsNone(pending.expires_at)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {credential_for(expired)}")
        self.assertEqual(client.post("/api/v1/ratings/", {"value": 5}, format="json").status_code, 201)
        self.assertEqual(CustomerRating.objects.count(), 2)
        self.assertEqual(OutboxEvent.objects.filter(event_type="ratings.received").count(), 2)
