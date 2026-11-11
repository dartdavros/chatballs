"""The picker projects known business guards without guessing future inputs."""

from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.manual_catalog_testing import ManualCatalogCase
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.tenancy.database import tenant_atomic


class ManualCatalogConditionTests(ManualCatalogCase):
    def scenarios(self):
        return [row for row in self.menu(summary="1")["items"] if row["kind"] == "scenario"]

    def test_known_contact_condition_hides_unavailable_scenario(self):
        with tenant_atomic(self.context):
            row = self.scenario()
            self.set_document(row, conditions={"mode": "all", "items": [
                {"kind": "context_present", "path": "contact", "present": True}]})
        self.assertEqual([item["id"] for item in self.scenarios()], [str(row.public_id)])
        with tenant_atomic(self.context):
            # Every persisted conversation must retain its contact.
            self.set_document(row, conditions={"mode": "all", "items": [
                {"kind": "context_present", "path": "contact", "present": False}]})
        self.assertEqual(self.scenarios(), [])
        with self.assertRaisesMessage(ExecutionDenied, "operation_unavailable"):
            self.menu(kind="scenario", id=str(row.public_id))
        with self.assertRaisesMessage(ExecutionDenied, "conditions_not_met"):
            launch(tenant=self.context, scenario_id=row.public_id, trigger_key="contact-guard",
                   conversation_id=self.conversation.pk, parameters={}, preview=True)

    def test_future_form_condition_is_visible_and_rechecked_with_actual_input(self):
        with tenant_atomic(self.context):
            row = self.scenario()
            self.set_document(row,
                parameters={"type": "object", "properties": {"choice": {"type": "string", "required": True}}},
                conditions={"mode": "all", "items": [{"left": {"source": "parameter", "name": "choice"},
                    "op": "eq", "right": {"source": "constant", "value": "yes"}}]})
        self.assertEqual([item["id"] for item in self.scenarios()], [str(row.public_id)])
        self.assertEqual(self.menu(kind="scenario", id=str(row.public_id))["item"]["id"], str(row.public_id))
        with self.assertRaisesMessage(ExecutionDenied, "conditions_not_met"):
            launch(tenant=self.context, scenario_id=row.public_id, trigger_key="false-guard",
                   conversation_id=self.conversation.pk, parameters={"choice": "no"}, preview=True)
        preview, _ = launch(tenant=self.context, scenario_id=row.public_id, trigger_key="true-guard",
                            conversation_id=self.conversation.pk, parameters={"choice": "yes"}, preview=True)
        self.assertIn("confirmation", preview)

    def test_existing_entity_link_hides_no_link_action_and_invalidates_detail(self):
        with tenant_atomic(self.context):
            row = self.scenario()
            self.set_document(row, conditions={"mode": "all", "items": [{"kind": "no_link",
                "connection": self.service.pk, "entity": "lead"}]})
        self.assertEqual([item["id"] for item in self.scenarios()], [str(row.public_id)])
        with tenant_atomic(self.context):
            EntityLink.objects.create(organization=self.organization, integration=self.service,
                internal_kind="conversation", internal_id=self.conversation.pk, external_kind="lead", external_id="crm-lead")
        self.assertEqual(self.scenarios(), [])
        with self.assertRaises(ExecutionDenied):
            self.menu(kind="scenario", id=str(row.public_id))
