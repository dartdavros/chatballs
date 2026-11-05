"""An exact native grant never widens its conversation/contact boundary."""

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.models import ConversationLabel
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.tenancy.database import tenant_atomic


class NativeScopeTests(CommentTransactionTestBase):
    def grant(self, key, scope):
        with tenant_atomic(self.context):
            return ActionGrant.objects.create(organization=self.organization,
                membership=self.context.membership, native_key=key,
                operation_key="", scope=scope)

    def test_conversation_grant_cannot_perform_organization_write_even_for_owner(self):
        self.grant("labels.post", "conversation")
        run, _ = execute_action(self.context, "labels.post", {"name": "Outside scope"},
            conversation_id=self.conversation.pk)
        with tenant_atomic(self.context):
            self.assertEqual(run.state, "failed")
            self.assertEqual(run.steps.get().error_code, "context")
            self.assertFalse(ConversationLabel.objects.exists())

    def test_owner_organization_action_from_chat_has_organization_scope_and_replays(self):
        run, _ = execute_action(self.context, "labels.post", {"name": "Organization label"},
            conversation_id=self.conversation.pk)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(run.state, "completed")
            self.assertEqual(run.definition["document"]["access"]["scope"], "organization")
            self.assertEqual(ConversationLabel.objects.count(), 1)

    def test_contact_grant_rejects_another_visible_contact_but_updates_current_contact(self):
        self.grant("contacts.card.patch", "contact")
        with tenant_atomic(self.context):
            other = self.make_conversation(self.organization, "other-visible")
        denied, _ = execute_action(self.context, "contacts.card.patch",
            {"contact_id": other.contact_id, "name": "Wrong contact"},
            conversation_id=self.conversation.pk)
        allowed, _ = execute_action(self.context, "contacts.card.patch",
            {"contact_id": self.conversation.contact_id, "name": "Current contact"},
            conversation_id=self.conversation.pk)
        with tenant_atomic(self.context):
            self.assertEqual(denied.state, "failed")
            self.assertEqual(allowed.state, "completed", allowed.steps.get().error_code)
            other.contact.refresh_from_db()
            self.assertNotEqual(other.contact.name, "Wrong contact")
            self.conversation.contact.refresh_from_db()
            self.assertEqual(self.conversation.contact.name, "Current contact")

    def test_scenario_conversation_scope_clamps_owner_organization_authority(self):
        with tenant_atomic(self.context):
            document = empty_definition()
            document["access"].update(scope="conversation", staff=[self.context.actor_user.pk])
            document["steps"] = [{"id": "global", "kind": "action", "connection": "chatballs",
                "target": "chatballs:labels.post", "inputs": {
                    "name": {"source": "constant", "value": "Outside scenario scope"}}}]
            scenario = ScenarioDefinition(organization=self.organization, name="Scoped action", enabled=True)
            scenario.definition = document
            scenario.save()
        run, _ = launch(tenant=self.context, scenario_id=scenario.public_id,
            trigger_key="clamped-owner", parameters={}, conversation_id=self.conversation.pk)
        with tenant_atomic(self.context):
            digest = invocation_digest(run.steps.get(), run)
        control(tenant=self.context, public_id=run.public_id, action="approve", digest=digest)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertEqual(run.steps.get().error_code, "context")
            self.assertFalse(ConversationLabel.objects.exists())

    def test_current_scenario_scope_narrows_an_older_organization_snapshot(self):
        with tenant_atomic(self.context):
            other = self.make_conversation(self.organization, "other-policy-target")
            document = empty_definition()
            document["access"].update(scope="organization", staff=[self.context.actor_user.pk])
            document["steps"] = [{"id": "comment", "kind": "action", "connection": "chatballs",
                "target": "chatballs:comments.post", "inputs": {
                    "conversation_id": {"source": "constant", "value": str(other.pk)},
                    "text": {"source": "constant", "value": "Outside the current policy"}}}]
            scenario = ScenarioDefinition(organization=self.organization, name="Narrowed action", enabled=True)
            scenario.definition = document
            scenario.save()
        run, _ = launch(tenant=self.context, scenario_id=scenario.public_id,
            trigger_key="changed-policy", parameters={}, conversation_id=self.conversation.pk)
        with tenant_atomic(self.context):
            document["access"]["scope"] = "conversation"
            scenario.definition = document
            scenario.save()
            self.assertEqual(run.definition["document"]["access"]["scope"], "organization")
            digest = invocation_digest(run.steps.get(), run)
        control(tenant=self.context, public_id=run.public_id, action="approve", digest=digest)
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            run.refresh_from_db()
            self.assertEqual(run.state, "failed")
            self.assertEqual(run.steps.get().error_code, "context")
            self.assertFalse(ConversationComment.objects.exists())
