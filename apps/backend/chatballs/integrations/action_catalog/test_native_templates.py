"""Native grants do not widen personal libraries or grant management authority."""

from chatballs.conversations import template_services
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.template_models import ReplyTemplateManagementGrant
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeTemplateTests(CommentTransactionTestBase):
    def setUp(self):
        super().setUp()
        user = HumanUser.objects.create_user(email="library@native.test")
        self.member = OrganizationMembership.objects.create(organization=self.organization,
            user=user, role="EMPLOYEE")
        self.tenant = TenantContext.for_membership(self.member)

    def allow(self, key, *, scope="organization"):
        with tenant_atomic(self.tenant):
            ActionGrant.objects.create(organization=self.organization, membership=self.member,
                native_key=key, operation_key="", scope=scope)

    def test_personal_search_and_direct_id_keep_the_same_owner_boundary(self):
        self.allow("templates.post")
        self.allow("templates.get")
        self.allow("templates.template.get")
        with tenant_atomic(self.context):
            other = template_services.create_template(self.context,
                {"title": "Private management", "text": "Private", "scope": "PERSONAL"})["template"]
        run, output = execute_action(self.tenant, "templates.post",
            {"title": "Personal greeting", "text": "Hello", "scope": "PERSONAL"})
        self.assertEqual(run.state, "completed")
        mine = output["template"]
        self.assertEqual(mine["ownerId"], self.member.pk)
        run, output = execute_action(self.tenant, "templates.get", {"q": ""})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [mine["id"]])
        run, _ = execute_action(self.tenant, "templates.template.get", {"template_id": other["id"]})
        self.assertEqual(run.state, "failed")

    def test_action_grant_cannot_self_assign_shared_library_management(self):
        self.allow("templates.management_grant.patch")
        run, _ = execute_action(self.tenant, "templates.management_grant.patch",
            {"membership_id": self.member.pk, "granted": True})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.tenant):
            self.assertFalse(ReplyTemplateManagementGrant.objects.filter(membership=self.member).exists())
            self.member.refresh_from_db()
            self.assertEqual(self.member.role, "EMPLOYEE")

    def test_render_keeps_unfilled_markers_and_uses_the_visible_conversation(self):
        with tenant_atomic(self.context):
            template = template_services.create_template(self.context, {"title": "Greeting",
                "text": "Hello {{client_name}} {{contact.phone}}", "scope": "SHARED"})["template"]
        run, output = execute_action(self.context, "templates.render.post",
            {"template_id": template["id"]}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["text"], "Hello Customer {{contact.phone}}")
        self.assertEqual(output["unfilledKeys"], ["contact.phone"])
