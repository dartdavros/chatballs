"""Catalog, form, preview, launch and lookups respect current employee authority."""

from unittest.mock import patch

from chatballs.conversations.access import require_conversation_action
from chatballs.identity.models import EmployeeGroup
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.integrations.execution.launch import launch, launch_direct
from chatballs.integrations.execution.lookup_queries import manual as manual_lookup
from chatballs.integrations.execution.manual_catalog_queries import catalog
from chatballs.integrations.execution.manual_catalog_testing import ManualCatalogCase
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class ManualCatalogAccessTests(ManualCatalogCase):
    def test_supervision_view_is_not_direct_service_operate_permission(self):
        tenant = self.employee("SUPERVISOR")
        with tenant_atomic(self.context):
            group = EmployeeGroup.objects.create(organization=self.organization, name="Supervised")
            self.conversation.group = group
            self.conversation.save(update_fields=["group"])
            EmployeeGroupSupervision.objects.create(employee=tenant.membership, group=group)
            ActionGrant.objects.create(organization=self.organization, membership=tenant.membership,
                integration=self.service, operation_key="lead.create", scope="conversation")
            require_conversation_action(tenant, self.conversation, "conversations.view")
        self.assertEqual(self.menu(tenant=tenant, summary="1")["items"], [])
        for preview in (True, False):
            with self.assertRaisesMessage(ExecutionDenied, "permission"):
                launch_direct(tenant=tenant, connection_id=self.service.pk, operation_key="lead.create",
                    conversation_id=self.conversation.pk, trigger_key="supervised", arguments={"fields": {}}, preview=preview,
                    manual_validation=True)
        with patch("chatballs.integrations.execution.lookup_queries.load_lookup", side_effect=AssertionError("network")):
            with self.assertRaisesMessage(ExecutionDenied, "permission"):
                manual_lookup(tenant, {"conversation": str(self.conversation.pk), "connection": str(self.service.pk),
                                      "operation": "lead.create", "lookup": "users"})

    def test_missing_native_grant_is_hidden_and_rechecked_at_preview(self):
        tenant = self.employee()
        with tenant_atomic(self.context):
            scenario = self.scenario(staff=[tenant.actor_user.pk])
        self.assertEqual(self.menu(tenant=tenant)["items"], [])
        with tenant_atomic(self.context):
            grant = ActionGrant.objects.create(organization=self.organization, membership=tenant.membership,
                native_key="comments.get", operation_key="", scope="conversation")
        self.assertEqual([item["id"] for item in self.menu(tenant=tenant, summary="1")["items"]], [str(scenario.public_id)])
        with tenant_atomic(self.context):
            grant.enabled = False
            grant.save(update_fields=["enabled"])
        with self.assertRaises(ExecutionDenied):
            self.menu(tenant=tenant, kind="scenario", id=str(scenario.public_id))
        for preview in (True, False):
            with self.assertRaisesMessage(ExecutionDenied, "permission"):
                launch(tenant=tenant, scenario_id=scenario.public_id, trigger_key="revoked-native",
                       parameters={}, conversation_id=self.conversation.pk, preview=preview, manual_validation=True)
        with tenant_atomic(self.context):
            self.assertFalse(ScenarioRun.objects.exists())

    def test_bound_conversation_cannot_be_widened_by_scenario(self):
        tenant = self.employee()
        with tenant_atomic(self.context):
            row = self.scenario(staff=[tenant.actor_user.pk])
            ActionGrant.objects.create(organization=self.organization, membership=tenant.membership,
                native_key="comments.get", operation_key="", scope="conversation")
            block = self.native_step()
            block["inputs"]["conversation_id"] = {"source": "constant", "value": str(self.foreign_conversation.pk)}
            self.set_document(row, steps=[block])
        self.assertEqual(self.menu(tenant=tenant)["items"], [])

    def test_native_grant_cannot_give_an_employee_an_administrative_capability(self):
        tenant = self.employee()
        with tenant_atomic(self.context):
            self.scenario(staff=[tenant.actor_user.pk], scope="organization", steps=[{
                "id": "settings", "kind": "action", "connection": "chatballs",
                "target": "chatballs:settings.get", "inputs": {}}])
            ActionGrant.objects.create(organization=self.organization, membership=tenant.membership,
                native_key="settings.get", operation_key="", scope="organization")
        self.assertEqual(catalog(tenant, {"summary": "1"})["items"], [])

    def test_known_contact_target_must_match_the_bound_dialog(self):
        with tenant_atomic(self.context):
            row = self.scenario(steps=[{"id": "contact", "kind": "action", "connection": "chatballs",
                "target": "chatballs:contacts.card.get", "inputs": {"contact_id": {
                    "source": "constant", "value": str(self.foreign_conversation.contact_id)}}}])
        self.assertNotIn(str(row.public_id), {item["id"] for item in self.menu(summary="1")["items"]})

    def test_nested_staff_policy_delegation_trigger_and_enabled_are_checked(self):
        tenant = self.employee()
        with tenant_atomic(self.context):
            child = self.scenario(name="Child", staff=[tenant.actor_user.pk], delegated=True)
            self.set_document(child, triggers=[{"id": "child", "kind": "scenario"}])
            parent = self.scenario(name="Parent", staff=[tenant.actor_user.pk], steps=[{
                "id": "child", "kind": "call", "scenario": str(child.public_id), "inputs": {}}])
            ActionGrant.objects.create(organization=self.organization, membership=tenant.membership,
                native_key="comments.get", operation_key="", scope="conversation")
            allowed = child.definition
        self.assertEqual([row["id"] for row in self.menu(tenant=tenant)["items"]], [str(parent.public_id)])
        for change in ({"access": {**allowed["access"], "delegated": False}},
                       {"access": {**allowed["access"], "staff": []}}, {"triggers": []}):
            with tenant_atomic(self.context):
                child.definition = {**allowed, **change}
                child.save(update_fields=["content"])
            self.assertEqual(self.menu(tenant=tenant)["items"], [])
            with self.assertRaises(ExecutionDenied):
                self.menu(tenant=tenant, kind="scenario", id=str(parent.public_id))
        with tenant_atomic(self.context):
            child.definition = allowed
            child.enabled = False
            child.save()
        self.assertEqual(self.menu(tenant=tenant)["items"], [])
