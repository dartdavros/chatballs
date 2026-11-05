"""The chat menu is a contextual projection, not the native API inventory."""

from django.utils import timezone

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.registry import native_actions
from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.execution.manual_catalog_queries import catalog
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ChatCatalogTests(CommentTestBase):
    def scenario(self, name, *, scope="conversation", staff=(), trigger="staff", enabled=True):
        document = empty_definition()
        document["access"].update(scope=scope, staff=list(staff))
        document["triggers"] = [{"id": trigger, "kind": trigger}]
        document["steps"] = [{"id": "comments", "kind": "action", "connection": "chatballs",
            "target": "chatballs:comments.get", "inputs": {
                "conversation_id": {"source": "context", "path": "conversation.id"}}}]
        row = ScenarioDefinition(organization=self.organization, name=name, enabled=enabled)
        row.definition = document
        row.save()
        return row

    def menu(self, tenant=None):
        return catalog(tenant or self.context, {"conversation": str(self.conversation.pk)})["items"]

    def test_admin_menu_has_only_enabled_contextual_staff_scenarios(self):
        with tenant_atomic(self.context):
            self.membership.role = "ADMIN"
            self.membership.save(update_fields=["role"])
            expected = {str(self.scenario("Conversation").public_id),
                        str(self.scenario("Contact", scope="contact").public_id)}
            self.scenario("Organization administration", scope="organization")
            self.scenario("Automatic only", trigger="scenario")
            self.scenario("Disabled", enabled=False)
        self.assertEqual({row["id"] for row in self.menu()}, expected)
        with tenant_atomic(self.context):
            self.assertTrue(native_actions())
            self.assertFalse(ScenarioRun.objects.exists())
            self.assertFalse(OutboxEvent.objects.filter(event_type="integrations.run").exists())

    def test_operator_sees_only_permitted_scenarios_and_revocation_still_applies(self):
        user = HumanUser.objects.create_user(email="operator@chat-catalog.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        tenant = TenantContext.for_membership(member)
        with tenant_atomic(self.context):
            permitted = self.scenario("Permitted", staff=[user.pk])
            self.scenario("Not delegated")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="comments.get", operation_key="", scope="conversation")
        self.assertEqual([row["id"] for row in self.menu(tenant)], [str(permitted.public_id)])
        with tenant_atomic(self.context):
            document = permitted.definition
            document["access"]["staff"] = []
            permitted.definition = document
            permitted.save(update_fields=["content"])
        self.assertEqual(self.menu(tenant), [])
        with tenant_atomic(tenant), self.assertRaises(ExecutionDenied):
            authorize(tenant, document, self.conversation.pk, scenario_id=permitted.pk)

    def test_archived_context_hides_even_permitted_contact_actions(self):
        with tenant_atomic(self.context):
            expected = self.scenario("Contact required", scope="contact")
        self.assertEqual([row["id"] for row in self.menu()], [str(expected.public_id)])
        with tenant_atomic(self.context):
            self.conversation.archived_at = timezone.now()
            self.conversation.save(update_fields=["archived_at"])
        self.assertEqual(self.menu(), [])

    def test_service_operations_keep_connection_metadata_and_exact_employee_grants(self):
        user = HumanUser.objects.create_user(email="service@chat-catalog.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        tenant = TenantContext.for_membership(member)
        with tenant_atomic(self.context):
            service = Integration.objects.create(organization=self.organization, name="CRM", kind="SERVICE",
                provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(integration=service, adapter_key=ADAPTER.key,
                adapter_version=ADAPTER.contract_version, auth_method=ADAPTER.auth_methods[0].key, credentials="{}")
            operation = ADAPTER.operations[0]
            ActionGrant.objects.create(organization=self.organization, membership=member,
                integration=service, operation_key=operation.key, scope="conversation")
        admin_items = self.menu()
        self.assertTrue(admin_items)
        self.assertTrue(all(row["connectionId"] == service.pk for row in admin_items))
        employee_items = self.menu(tenant)
        self.assertEqual([row["operationKey"] for row in employee_items], [operation.key])
        self.assertEqual(employee_items[0]["connection"], "CRM")
        self.assertIn("readOnly", employee_items[0])
        with tenant_atomic(self.context):
            service.is_active = False
            service.save(update_fields=["is_active"])
        unavailable = self.menu(tenant)[0]
        self.assertFalse(unavailable["available"])
        self.assertTrue(unavailable["reason"])
