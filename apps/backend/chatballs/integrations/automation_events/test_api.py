"""Real scoped endpoint and key revocation; no substitute API server."""

import json

from django.test import Client

from chatballs.integrations.automation_events.configuration import synchronize
from chatballs.integrations.execution.composition_testing import CompositionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey
from chatballs.integrations.scenarios.external_keys import token_hash
from chatballs.tenancy.database import tenant_atomic


class ScopedAPITests(CompositionCase):
    def setUp(self):
        super().setUp()
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"] = [self.action("project")]
            document["triggers"] = [{"id": "api", "kind": "api"}]
            document["access"]["delegated"] = True
            self.scenario.definition = document
            self.scenario.save()
            synchronize(self.tenant, self.scenario, {})
            self.key = ScenarioExternalKey.objects.create(organization=self.organization,
                scenario=self.scenario, trigger_id="api", token_hash=token_hash("cbk_secret"))
        self.endpoint = f"/api/v1/scenario-triggers/{self.key.public_id}/"
        self.http = Client()

    def send(self, body=None, *, token="cbk_secret", key="one"):
        return self.http.post(self.endpoint, json.dumps(body or {}), content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_IDEMPOTENCY_KEY=key)

    def test_scoped_key_idempotency_and_rotation(self):
        first = self.send()
        self.assertEqual(first.status_code, 202, first.content)
        with tenant_atomic(self.tenant):
            self.scenario.revision += 1
            self.scenario.save(update_fields=["revision"])
        repeat = self.send()
        self.assertEqual(repeat.json()["id"], first.json()["id"])
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 1)
            self.key.token_hash = token_hash("cbk_rotated")
            self.key.save()
        self.assertEqual(self.send().status_code, 401)
        self.assertEqual(self.send(token="cbk_rotated", key="two").status_code, 202)

    def test_untrusted_principal_and_missing_key_are_rejected(self):
        self.assertEqual(self.send(token="wrong").status_code, 401)
        self.assertEqual(self.send({"tenant": 123}).status_code, 400)
        self.assertEqual(self.send(key="").status_code, 400)
        with tenant_atomic(self.tenant):
            self.assertFalse(ScenarioRun.objects.exists())

    def test_scope_and_disabled_scenario_are_checked(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["access"]["scope"] = "conversation"
            self.scenario.definition = document
            self.scenario.save()
        self.assertEqual(self.send().status_code, 403)
        with tenant_atomic(self.tenant):
            self.scenario.enabled = False
            self.scenario.save()
        self.assertEqual(self.send().status_code, 403)
