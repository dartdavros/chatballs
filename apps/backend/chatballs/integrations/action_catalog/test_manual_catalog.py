"""A full catalog must not repeat authorization queries for each operation."""

from chatballs.conversations.comment_test_base import CommentTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.manual_catalog import manual_actions
from chatballs.integrations.action_catalog.registry import native_actions
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class ManualNativeCatalogTests(CommentTestBase):
    def test_manager_catalog_queries_depend_on_capabilities_not_action_count(self):
        actions = native_actions()
        with tenant_atomic(self.context):
            with self.assertNumQueries(1):
                items = manual_actions(self.context, [], self.conversation)
        self.assertEqual(len(items), len(actions))
        self.assertTrue(all(item["connectionId"] == "chatballs" for item in items))

    def test_employee_catalog_requires_exact_grant_and_its_context(self):
        user = HumanUser.objects.create_user(email="catalog@native.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        context = TenantContext.for_membership(member)
        with tenant_atomic(context):
            grant = ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="comments.get", operation_key="", scope="conversation")
            self.assertEqual(manual_actions(context, [grant], None), [])
            items = manual_actions(context, [grant], self.conversation)
        self.assertEqual([item["operationKey"] for item in items], ["comments.get"])
