"""Knowledge commands run through grants, runner and the original domain services."""

from chatballs.ai.models import AIAgent, Knowledge, KnowledgeCategory, KnowledgeFragment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.identity.models import AuditEvent, HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.adapters.contracts import RetryStrategy
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeKnowledgeTests(CommentTransactionTestBase):
    def test_crud_filters_index_and_receipt_replay(self):
        run, output = execute_action(self.context, "knowledge.post", {"title": "Guide", "content": "Product guide."})
        self.assertEqual(run.state, "completed")
        knowledge_id = output["knowledge"]["id"]
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(Knowledge.objects.filter(title="Guide").count(), 1)
            self.assertTrue(KnowledgeFragment.objects.filter(knowledge_id=knowledge_id).exists())
            self.assertEqual(AuditEvent.objects.filter(action="ai.knowledge_created").count(), 1)
        run, output = execute_action(self.context, "knowledge.detail.patch", {
            "knowledge_id": knowledge_id, "description": "Updated", "isEnabled": False})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["knowledge"]["description"], "Updated")
        run, output = execute_action(self.context, "knowledge.get", {"search": "Guide", "isEnabled": False})
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["id"] for row in output["items"]], [knowledge_id])
        run, output = execute_action(self.context, "knowledge.detail.get", {"knowledge_id": knowledge_id})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["knowledge"]["createdBy"], self.author.email)
        run, _ = execute_action(self.context, "knowledge.reindex.post", {"knowledge_id": knowledge_id})
        self.assertEqual(run.state, "completed")
        run, _ = execute_action(self.context, "knowledge.detail.delete", {"knowledge_id": knowledge_id})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(self.context):
            self.assertFalse(Knowledge.objects.filter(pk=knowledge_id).exists())
        self.assertEqual(native_action("knowledge.post").execution, "io")
        self.assertEqual(native_action("knowledge.post").operation.retry, RetryStrategy.NONE)

    def test_import_bulk_move_and_agent_links_preserve_content_audit(self):
        run, output = execute_action(self.context, "knowledge.import.post", {"documents": [
            {"title": "Manual", "content": "Manual content", "categoryPath": ["Products"]}]})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["created"], 1)
        with tenant_atomic(self.context):
            item = Knowledge.objects.get(title="Manual")
            category = KnowledgeCategory.objects.create(organization=self.organization, name="Guides")
            agent = AIAgent.objects.create(channel=self.conversation.channel)
        run, output = execute_action(self.context, "knowledge.bulk.move", {
            "knowledgeIds": [item.id], "categoryId": category.id})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["updated"], 1)
        run, output = execute_action(self.context, "knowledge.agent.select_category", {
            "agent_id": agent.id, "categoryId": category.id})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["addedKnowledgeIds"], [item.id])
        run, output = execute_action(self.context, "knowledge.bulk.agent", {
            "agentId": agent.id, "knowledgeIds": [item.id], "action": "detach"})
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["changedIds"], [item.id])
        with tenant_atomic(self.context):
            self.assertFalse(agent.knowledge_items.exists())
            self.assertTrue(AuditEvent.objects.filter(action="ai.agent_knowledge_detached", actor=self.author).exists())

    def test_foreign_target_and_granted_employee_still_cannot_manage_knowledge(self):
        foreign_context = TenantContext.for_membership(self.foreign_author.memberships.get())
        run, output = execute_action(foreign_context, "knowledge.post", {"title": "Foreign"})
        self.assertEqual(run.state, "completed")
        foreign_id = output["knowledge"]["id"]
        run, _ = execute_action(self.context, "knowledge.detail.delete", {"knowledge_id": foreign_id})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            user = HumanUser.objects.create_user(email="knowledge-employee@example.test")
            member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="EMPLOYEE")
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="knowledge.post", scope="organization")
        run, _ = execute_action(TenantContext.for_membership(member), "knowledge.post", {"title": "Forbidden"})
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(Knowledge.objects.filter(organization=self.organization).exists())
        with tenant_atomic(foreign_context):
            self.assertTrue(Knowledge.objects.filter(pk=foreign_id, organization=self.foreign).exists())
