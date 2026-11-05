"""Definition management keeps revisions, tenant boundaries and credentials."""

import json

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.management import save
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeScenarioTests(CommentTransactionTestBase):
    def execute(self, key, values, *, tenant=None, state="completed"):
        run, result = execute_action(tenant or self.context, key, values)
        self.assertEqual(run.state, state, run.steps.get().error_code)
        return run, result

    def test_create_update_copy_delete_and_revision_conflict_do_not_repeat(self):
        document = empty_definition()
        run, result = self.execute("scenarios.post", {"name": "Draft", "settings": {"definition": document}})
        row = result["scenario"]
        self.assertEqual(row["revision"], 1)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(ScenarioDefinition.objects.count(), 1)
            self.assertEqual(AuditEvent.objects.filter(action="integrations.scenario_saved").count(), 1)
            journal = run_payload(run, detail=True, tenant=self.context)
        self.assertEqual(journal["steps"][0]["arguments"]["settings"], {"redacted": True})
        _, updated = self.execute("scenarios.detail.put", {"public_id": row["id"], "revision": 1,
            "name": "Updated", "settings": {"definition": document}})
        self.assertEqual(updated["scenario"]["revision"], 2)
        self.execute("scenarios.detail.delete", {"public_id": row["id"], "revision": 1}, state="failed")
        _, copied = self.execute("scenarios.copy.post", {"public_id": row["id"], "name": "Copy"})
        self.assertNotEqual(copied["scenario"]["id"], row["id"])
        self.assertFalse(copied["scenario"]["enabled"])
        self.execute("scenarios.detail.delete", {"public_id": row["id"], "revision": 2})
        _, listed = self.execute("scenarios.get", {})
        self.assertEqual([item["name"] for item in listed["items"]], ["Copy"])

    def test_definition_outputs_hide_secret_inputs_and_external_credentials(self):
        secret = "ScenarioDefinitionCredential42"
        document = empty_definition()
        document["triggers"] = [{"id": "external", "kind": "api"}]
        document["steps"] = [{"id": "create", "kind": "action", "connection": "chatballs",
            "target": "chatballs:services.post", "inputs": {"name": {"source": "constant", "value": "CRM"},
                "values": {"source": "constant", "value": {"url": secret}}}}]
        _, created = self.execute("scenarios.post", {"name": "Secret draft", "settings": {"definition": document}})
        row = created["scenario"]
        self.assertNotIn(secret, json.dumps(created))
        self.assertNotIn("key", row["externalKeys"][0])
        _, read = self.execute("scenarios.detail.get", {"public_id": row["id"]})
        self.assertEqual(read["scenario"]["definition"]["steps"][0]["inputs"]["values"], {"redacted": True})
        with tenant_atomic(self.context):
            original = ScenarioDefinition.objects.get(public_id=row["id"])
            self.assertIn(secret, json.dumps(original.definition))

    def test_permissions_foreign_rows_validation_and_catalog_budget(self):
        foreign = TenantContext.for_membership(self.foreign_author.memberships.get(organization=self.foreign))
        row = save(foreign, {"name": "Foreign", "definition": empty_definition()})["scenario"]
        self.execute("scenarios.detail.get", {"public_id": row["id"]}, state="failed")
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="native-scenario-employee@example.test")
            membership = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=membership,
                native_key="scenarios.post", scope="organization")
        self.execute("scenarios.post", {"name": "Denied", "settings": {"definition": empty_definition()}},
            tenant=TenantContext.for_membership(membership), state="failed")
        _, checked = self.execute("scenarios.check.post", {"settings": {"definition": empty_definition()}})
        self.assertFalse(checked["valid"])
        _, catalog = self.execute("scenarios.catalog.get", {})
        self.assertTrue(any(row["key"] == "chatballs:scenarios.post" for row in catalog["nativeActions"]))
        self.assertLess(len(json.dumps(catalog).encode()), 4 * 1024 * 1024)
