"""Real PostgreSQL + common runner with an independent conditional-write adapter."""

from django.test import override_settings
from django.utils import timezone

from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation
from chatballs.integrations.adapters.registry import default_registry, reset_registry
from chatballs.integrations.execution import exchange_contract_testing as adapter
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.models import ServiceConnectionSettings
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.scenario_state.synchronization import (
    ServiceSynchronizationSettings,
    SynchronizationCheckpoint,
)
from chatballs.integrations.scenarios.conflicts import digest, resolve
from chatballs.integrations.scenarios.synchronization_runtime import start_cycle
from chatballs.tenancy.database import tenant_atomic


class ExchangeRuntimeTests(CompositionCase):
    def setUp(self):
        super().setUp()
        self.enterContext(override_settings(CHATBALLS_SERVICE_ADAPTERS=("chatballs.integrations.execution.exchange_contract_testing",)))
        reset_registry()
        self.registry = default_registry()
        adapter.RECORDS.clear()
        adapter.WRITES.clear()
        adapter.RECEIPTS.clear()
        adapter.RECORDS["person-1"] = {"displayName": "Remote", "version": "1", "modifiedAt": timezone.now().isoformat()}
        with tenant_atomic(self.tenant):
            ServiceConnectionSettings.objects.filter(integration=self.integration).update(adapter_key=adapter.ADAPTER.key, adapter_version=1, auth_method="public", credentials="{}")
            self.contact = Contact.objects.create(organization=self.organization, name="Local", email="same@example.test")
            self.channel = Channel.objects.create(organization=self.organization, code="exchange", name="Exchange")
            self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel, contact=self.contact)
            self.link = EntityLink.objects.create(organization=self.organization, integration=self.integration, internal_kind="contact",
                internal_id=self.contact.pk, external_kind="person", external_id="person-1")
            self.settings = ServiceSynchronizationSettings(organization=self.organization, integration=self.integration, delegate=self.tenant.membership)
            self.pair = {"id": "pair", "enabled": True, "left": {"connection": "chatballs", "entity": "contact"},
                "right": {"connection": str(self.integration.pk), "entity": "person"}, "direction": "both",
                "fields": [{"left": "name", "right": "displayName", "direction": "forward"},
                           {"left": "name", "right": "displayName", "direction": "reverse"}],
                "sourceOfTruth": "left", "conflict": "source", "deletion": "unlink", "causality": {"suppressEcho": True, "requireExplicitLink": True}}
            self.settings.definition = {"version": 1, "synchronization": [self.pair]}
            self.settings.save()
            self.checkpoint = SynchronizationCheckpoint(organization=self.organization, settings=self.settings, link=self.link, pair_id="pair", due_at=timezone.now())
            self.checkpoint.definition = {}
            self.checkpoint.save()

    def start_exchange(self, **policy):
        with tenant_atomic(self.tenant):
            self.pair.update(policy)
            self.settings.definition = {"version": 1, "synchronization": [self.pair]}
            self.settings.save()
            self.checkpoint.refresh_from_db()
            start_cycle(self.tenant, self.checkpoint, registry=self.registry)
            return self.checkpoint.run

    def drive(self, run):
        for _ in range(70):
            run_one(self.tenant, run.public_id, registry=self.registry)
            with tenant_atomic(self.tenant):
                run.refresh_from_db()
                if run.finished_at or run.state in {"decision", "unknown", "approval"}:
                    return run
        self.fail("Exchange did not settle")

    def test_common_runner_updates_and_echo_does_not_write_again(self):
        run = self.drive(self.start_exchange())
        self.assertEqual(run.state, "completed")
        self.assertEqual(adapter.RECORDS["person-1"]["displayName"], "Local")
        self.assertEqual(len(adapter.WRITES), 1)
        self.assertTrue(adapter.WRITES[0][3])
        again = self.drive(self.start_exchange())
        self.assertEqual(again.state, "completed")
        self.assertEqual(len(adapter.WRITES), 1)

    def test_reverse_updates_contact_without_merging_email_identity(self):
        with tenant_atomic(self.tenant):
            Contact.objects.create(organization=self.organization, name="Unrelated", email=self.contact.email)
        run = self.drive(self.start_exchange(sourceOfTruth="right"))
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.tenant):
            self.contact.refresh_from_db()
            self.assertEqual(self.contact.name, "Remote")
            self.assertIsNone(self.contact.merged_into_id)
            self.assertEqual(Contact.objects.filter(email=self.contact.email).count(), 2)

    def test_manual_choice_is_not_an_effect_until_runner_applies_it(self):
        run = self.drive(self.start_exchange(conflict="manual"))
        self.assertEqual(run.state, "decision")
        with tenant_atomic(self.tenant):
            self.checkpoint.refresh_from_db()
            token = digest(self.checkpoint)
            choices = {item["id"]: "left" for item in self.checkpoint.definition["conflicts"]}
        self.assertEqual(adapter.WRITES, [])
        resolve(self.tenant, run.public_id, expected_digest=token, choices=choices)
        self.assertEqual(adapter.WRITES, [])
        self.drive(run)
        self.assertEqual(run.state, "completed")
        self.assertEqual(adapter.RECORDS["person-1"]["displayName"], "Local")

    def test_new_remote_version_rejects_stale_resolution_without_overwriting(self):
        run = self.drive(self.start_exchange(conflict="manual"))
        with tenant_atomic(self.tenant):
            self.checkpoint.refresh_from_db()
            token = digest(self.checkpoint)
            choices = {item["id"]: "left" for item in self.checkpoint.definition["conflicts"]}
        adapter.RECORDS["person-1"].update(displayName="Newer", version="2")
        resolve(self.tenant, run.public_id, expected_digest=token, choices=choices)
        self.drive(run)
        self.assertEqual(run.state, "failed")
        self.assertEqual(adapter.RECORDS["person-1"]["displayName"], "Newer")
        self.assertEqual(adapter.WRITES, [])

    def test_remote_deletion_unlinks_without_deleting_native_contact(self):
        adapter.RECORDS["person-1"].update(deleted=True, version="2")
        run = self.drive(self.start_exchange())
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.tenant):
            self.link.refresh_from_db()
            self.assertFalse(self.link.active)
            self.assertTrue(Contact.objects.filter(pk=self.contact.pk).exists())

    def test_cancel_manual_conflict_finishes_without_effects(self):
        from chatballs.integrations.execution.control import control

        run = self.drive(self.start_exchange(conflict="manual"))
        self.assertEqual(run.state, "decision")
        control(tenant=self.tenant, public_id=run.public_id, action="cancel")
        self.drive(run)
        self.assertEqual(run.state, "cancelled")
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(adapter.WRITES, [])
        with tenant_atomic(self.tenant):
            self.contact.refresh_from_db()
            self.assertEqual(self.contact.name, "Local")

    def test_link_search_requires_explicit_candidate_and_current_revision(self):
        from chatballs.integrations.scenario_state.runs import ScenarioRun

        adapter.RECORDS["person-2"] = {"displayName": "Another Remote", "version": "1", "modifiedAt": timezone.now().isoformat()}
        base = f"/api/v1/organizations/{self.organization.public_id}/integrations/entity-links/{self.link.pk}/"
        query = f"?conversation={self.conversation.pk}"
        response = self.client.post(base + "search/" + query, {"query": "Remote", "triggerKey": "reference-search"}, format="json")
        self.assertEqual(response.status_code, 202, response.content)
        with tenant_atomic(self.tenant):
            run = ScenarioRun.objects.get(public_id=response.json()["runId"])
        self.drive(run)
        response = self.client.get(base + "search/" + query + f"&run={run.public_id}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()["items"]), 2)
        with tenant_atomic(self.tenant):
            self.link.refresh_from_db()
            self.assertEqual(self.link.external_id, "person-1")
        payload = {"action": "replace", "revision": 1, "externalId": "unlisted", "searchRunId": str(run.public_id)}
        self.assertEqual(self.client.post(base + query, payload, format="json").status_code, 409)
        payload["externalId"] = "person-2"
        response = self.client.post(base + query, payload, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.post(base + query, payload, format="json").status_code, 409)
        response = self.client.post(base + query, {"action": "unlink", "revision": 2}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(adapter.WRITES, [])
        with tenant_atomic(self.tenant):
            self.link.refresh_from_db()
            self.assertFalse(self.link.active)

    def test_search_no_results_keeps_existing_link(self):
        from chatballs.integrations.scenario_state.runs import ScenarioRun

        base = f"/api/v1/organizations/{self.organization.public_id}/integrations/entity-links/{self.link.pk}/search/"
        query = f"?conversation={self.conversation.pk}"
        response = self.client.post(base + query, {"query": "missing", "triggerKey": "empty-search"}, format="json")
        self.assertEqual(response.status_code, 202, response.content)
        with tenant_atomic(self.tenant):
            run = ScenarioRun.objects.get(public_id=response.json()["runId"])
        self.drive(run)
        response = self.client.get(base + query + f"&run={run.public_id}")
        self.assertEqual(response.json()["items"], [])
        with tenant_atomic(self.tenant):
            self.link.refresh_from_db()
            self.assertEqual(self.link.external_id, "person-1")

    def test_native_receipt_recovers_after_runner_commit_crash(self):
        from datetime import timedelta
        from unittest.mock import patch

        from chatballs.integrations.execution import runner

        run = self.start_exchange(sourceOfTruth="right")
        original = runner._commit

        def commit(tenant, token, result, **kwargs):
            with tenant_atomic(tenant):
                native = run.steps.filter(operation_key="synchronization.local", state="running").first()
                # The receipt is durable before the runner's separate commit.
                if native and "nativeResult" in native.definition:
                    raise RuntimeError("after native commit")
            return original(tenant, token, result, **kwargs)

        crashed = False
        with patch.object(runner, "_commit", side_effect=commit):
            for _ in range(60):
                try:
                    runner.run_one(self.tenant, run.public_id, registry=self.registry)
                except RuntimeError:
                    crashed = True
                    break
        self.assertTrue(crashed)
        with tenant_atomic(self.tenant):
            self.contact.refresh_from_db()
            self.assertEqual(self.contact.name, "Remote")
            from chatballs.integrations.scenario_state.entity_links import IntegrationEntityVersion
            version = IntegrationEntityVersion.objects.get(internal_kind="contact", internal_id=self.contact.pk).version
            expired = timezone.now() - timedelta(seconds=1)
            run.steps.filter(state="running").update(lease_until=expired, due_at=expired)
        self.drive(run)
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.tenant):
            self.assertEqual(IntegrationEntityVersion.objects.get(internal_kind="contact", internal_id=self.contact.pk).version, version)

    def test_runtime_rls_hides_foreign_link(self):
        base = f"/api/v1/organizations/{self.other.public_id}/integrations/entity-links/{self.link.pk}/"
        response = self.as_runtime(lambda: self.client_for(self.other_owner).post(
            base + f"?conversation={self.conversation.pk}", {"action": "unlink", "revision": 1}, format="json"))
        self.assertEqual(response.status_code, 404)
        with tenant_atomic(self.tenant):
            self.link.refresh_from_db()
            self.assertTrue(self.link.active)

    def test_retention_clears_disabled_checkpoint_without_run(self):
        from datetime import timedelta

        from chatballs.integrations.scenarios.synchronization_retention import clear_inactive

        now = timezone.now()
        with tenant_atomic(self.tenant):
            self.pair["enabled"] = False
            self.settings.definition = {"version": 1, "synchronization": [self.pair]}
            self.settings.save()
            ServiceSynchronizationSettings.objects.filter(pk=self.settings.pk).update(updated_at=now - timedelta(days=8))
            self.checkpoint.definition = {"baseline": {"private": "obsolete"}}
            self.checkpoint.save()
            clear_inactive(self.tenant, now=now, days=7)
            self.checkpoint.refresh_from_db()
            self.assertEqual(self.checkpoint.definition, {})
