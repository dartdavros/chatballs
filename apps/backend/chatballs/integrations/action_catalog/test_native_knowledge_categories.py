"""Native category mutations keep hierarchy, immutable categories and tenant policy."""

from rest_framework.exceptions import PermissionDenied

from chatballs.ai import category_management
from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.ai.models import KnowledgeCategory
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeKnowledgeCategoryTests(CommentTransactionTestBase):
    def test_hierarchy_cycle_and_system_category_guards(self):
        run, output = execute_action(self.context, "knowledge.categories.post", {"name": "Root"})
        self.assertEqual(run.state, "completed")
        root = output["category"]["id"]
        run, output = execute_action(self.context, "knowledge.categories.post", {"name": "Child", "parentId": root})
        self.assertEqual(run.state, "completed")
        child = output["category"]["id"]
        run, _ = execute_action(self.context, "knowledge.category.patch", {"category_id": root, "parentId": child})
        self.assertEqual(run.state, "failed")
        run, _ = execute_action(self.context, "knowledge.category.delete", {"category_id": root})
        self.assertEqual(run.state, "failed")
        run, output = execute_action(self.context, "knowledge.categories.get", {})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [root, child])
        run, _ = execute_action(self.context, "knowledge.category.delete", {"category_id": child})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            system = ensure_uncategorized_category(self.organization)
        for key in ("knowledge.category.patch", "knowledge.category.delete"):
            run, _ = execute_action(self.context, key, {"category_id": system.id})
            self.assertEqual(run.state, "failed")

    def test_foreign_parent_rejected_and_employee_cannot_read_category_directory(self):
        with tenant_atomic(TenantContext.for_resource(self.foreign)):
            foreign = KnowledgeCategory.objects.create(organization=self.foreign, name="Foreign")
        run, _ = execute_action(self.context, "knowledge.categories.post", {"name": "Invalid", "parentId": foreign.id})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(KnowledgeCategory.objects.filter(organization=self.organization).exists())
        user = HumanUser.objects.create_user(email="employee@native-knowledge.test")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
        context = TenantContext.for_membership(member)
        with tenant_atomic(context), self.assertRaises(PermissionDenied):
            category_management.list_categories(context)
