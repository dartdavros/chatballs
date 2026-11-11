"""Small real-domain fixtures for the manual action catalog boundaries."""

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.execution.manual_catalog_queries import catalog
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ManualCatalogCase(CommentTestBase):
    def setUp(self):
        super().setUp()
        with tenant_atomic(self.context):
            self.service = Integration.objects.create(organization=self.organization, name="CRM workspace", kind="SERVICE",
                provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(integration=self.service, adapter_key=ADAPTER.key,
                adapter_version=ADAPTER.contract_version, auth_method=ADAPTER.auth_methods[0].key, credentials="{}")

    def scenario(self, *, name="Manual", steps=None, **access):
        document = empty_definition()
        document["access"].update(access)
        document["steps"] = steps if steps is not None else [self.native_step()]
        row = ScenarioDefinition(organization=self.organization, name=name, enabled=True)
        row.definition = document
        row.save()
        return row

    @staticmethod
    def native_step(key="comments.get"):
        return {"id": "operation", "kind": "action", "connection": "chatballs", "target": f"chatballs:{key}",
                "inputs": {"conversation_id": {"source": "context", "path": "conversation.id"}}}

    def employee(self, role="EMPLOYEE"):
        user = HumanUser.objects.create_user(email=f"manual-{role.lower()}@catalog.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role=role)
        return TenantContext.for_membership(member)

    def menu(self, *, tenant=None, **query):
        return catalog(tenant or self.context, {"conversation": str(self.conversation.pk), **query})

    @staticmethod
    def set_document(row, **changes):
        data = row.definition
        data.update(changes)
        row.definition = data
        row.save(update_fields=["content"])
