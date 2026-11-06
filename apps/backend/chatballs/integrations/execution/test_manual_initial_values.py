"""Real catalog/preview boundaries: no effects, guesses or cross-tenant data."""

from django.utils import timezone

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.conversations.models import Conversation
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import EmployeeGroup
from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.launch import launch, launch_direct
from chatballs.integrations.execution.manual_catalog_queries import catalog
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.database import tenant_atomic


class ManualInitialValuesTests(CommentTestBase):
    def setUp(self):
        super().setUp()
        with tenant_atomic(self.context):
            self.service = Integration.objects.create(organization=self.organization, name="CRM", kind="SERVICE",
                provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(integration=self.service, adapter_key=ADAPTER.key,
                adapter_version=1, auth_method="webhook", credentials="{}")

    def menu(self, conversation=None):
        return catalog(self.context, {"conversation": str((conversation or self.conversation).pk)})["items"]

    def contact(self, **values):
        with tenant_atomic(self.context):
            contact = self.conversation.contact
            for key, value in values.items():
                setattr(contact, key, value)
            contact.save(update_fields=list(values))

    def test_known_values_are_separate_from_schema_nested_and_have_no_side_effects(self):
        self.contact(name="Анна Петрова", email="anna@example.test", phone="+79991234567")
        expected = {"fields": {"NAME": "Анна Петрова",
            "EMAIL": [{"VALUE": "anna@example.test", "VALUE_TYPE": "WORK"}],
            "PHONE": [{"VALUE": "+79991234567", "VALUE_TYPE": "WORK"}]}}
        for item in self.menu():
            values = item["initialValues"]
            self.assertEqual(values, expected if item["operationKey"] in {"lead.create", "contact.create"} else {})
            if values:
                self.assertEqual(validate_value(ADAPTER.operation(item["operationKey"]).input, values), [])
                self.assertNotIn("initialValues", item["parameters"])
        with tenant_atomic(self.context):
            self.conversation.contact.refresh_from_db()
            self.assertEqual(self.conversation.contact.name, "Анна Петрова")
            self.assertFalse(ScenarioRun.objects.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.run").exists())

    def test_partial_unknown_and_changed_contexts_do_not_reuse_previous_values(self):
        self.contact(name=" ", email="known@example.test", phone="\t")
        item = next(row for row in self.menu() if row["operationKey"] == "contact.create")
        self.assertEqual(item["initialValues"], {"fields": {"EMAIL": [
            {"VALUE": "known@example.test", "VALUE_TYPE": "WORK"}]}})
        with tenant_atomic(self.context):
            other = self.make_conversation(self.organization, "other")
            other.contact.name = "Другой контакт"
            other.contact.save(update_fields=["name"])
        item = next(row for row in self.menu(other) if row["operationKey"] == "lead.create")
        self.assertEqual(item["initialValues"], {"fields": {"NAME": "Другой контакт"}})
        self.contact(email="")
        self.assertEqual(next(row for row in self.menu() if row["operationKey"] == "lead.create")["initialValues"], {})

    def test_foreign_invisible_and_revoked_actor_cannot_read_initial_values(self):
        with self.assertRaises(Conversation.DoesNotExist):
            self.menu(self.foreign_conversation)
        with tenant_atomic(self.context):
            self.conversation.group = EmployeeGroup.objects.create(organization=self.organization, name="Private")
            self.conversation.save(update_fields=["group"])
            self.membership.role = "EMPLOYEE"
            self.membership.save(update_fields=["role"])
        with self.assertRaises(Conversation.DoesNotExist):
            self.menu()
        with tenant_atomic(self.context):
            self.membership.blocked_at = timezone.now()
            self.membership.save(update_fields=["blocked_at"])
        with self.assertRaises(ExecutionDenied):
            self.menu()

    def test_preview_and_launch_use_exact_edits_and_preserve_employee_id(self):
        self.contact(email="known@example.test", phone="+79991234567")
        arguments = {"fields": {"NAME": "Исправлено", "PHONE": [], "EMAIL": [], "ASSIGNED_BY_ID": "001"}}
        preview, _ = launch_direct(tenant=self.context, connection_id=self.service.pk, operation_key="lead.create",
            trigger_key="manual-prefill", arguments=arguments, conversation_id=self.conversation.pk, preview=True)
        self.assertEqual(preview["arguments"], arguments)
        with tenant_atomic(self.context):
            self.assertFalse(ScenarioRun.objects.exists())
        run, _ = launch_direct(tenant=self.context, connection_id=self.service.pk, operation_key="lead.create",
            trigger_key="manual-prefill", arguments=arguments, conversation_id=self.conversation.pk,
            confirmation=preview["confirmation"])
        with tenant_atomic(self.context):
            self.assertEqual(run.steps.get().definition["arguments"], arguments)

    def test_saved_scenario_explicit_bindings_and_parameters_keep_priority(self):
        self.contact(email="known@example.test")
        document = empty_definition()
        document["access"].update(scope="contact", staff=[self.author.pk])
        document["steps"] = [{"id": "create", "kind": "action", "connection": str(self.service.pk),
            "target": "service:lead.create", "inputs": {"fields": {
                "NAME": {"source": "parameter", "name": "name"},
                "EMAIL": {"source": "constant", "value": []}}}}]
        document["parameters"] = {"type": "object", "properties": {"name": {"type": "string"}}}
        with tenant_atomic(self.context):
            scenario = ScenarioDefinition(organization=self.organization, name="Explicit", enabled=True)
            scenario.definition = document
            scenario.save()
        item = next(row for row in self.menu() if row["kind"] == "scenario")
        self.assertNotIn("initialValues", item)
        preview, _ = launch(tenant=self.context, scenario_id=scenario.public_id, trigger_key="explicit",
            parameters={"name": "Сценарий"}, conversation_id=self.conversation.pk, preview=True)
        self.assertEqual(preview["arguments"], {"fields": {"NAME": "Сценарий", "EMAIL": []}})
