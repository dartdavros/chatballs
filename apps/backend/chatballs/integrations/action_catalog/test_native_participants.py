"""Runner grants cannot bypass composition limits or source role restrictions."""

from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.conversations.participant_services import add_participant
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeParticipantTests(CommentTransactionTestBase):
    def member(self, suffix):
        user = HumanUser.objects.create_user(email=f"{suffix}@native-participants.test")
        return OrganizationMembership.objects.create(organization=self.organization,
            user=user, role="EMPLOYEE")

    def test_runner_enforces_limit_and_leaves_only_one_participation_episode(self):
        first, second = self.member("first"), self.member("second")
        with tenant_atomic(self.context):
            self.organization.additional_participant_limit = 1
            self.organization.save(update_fields=["additional_participant_limit"])
        run, output = execute_action(self.context, "participants.post",
            {"membership_id": first.pk, "reason": "Consultation"}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(output["participant"]["membershipId"], first.pk)
        run, _ = execute_action(self.context, "participants.post",
            {"membership_id": second.pk, "reason": "Exceeds limit"}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(ConversationParticipant.objects.filter(conversation=self.conversation).active().count(), 1)
        run, output = execute_action(self.context, "participants.get", {}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual([row["membershipId"] for row in output["items"]], [first.pk])

    def test_explicit_grant_does_not_allow_additional_participant_to_manage_composition(self):
        specialist, target = self.member("specialist"), self.member("target")
        with tenant_atomic(self.context):
            add_participant(context=self.context, conversation_id=self.conversation.pk,
                membership_id=specialist.pk, reason="Consultation")
            ActionGrant.objects.create(organization=self.organization, membership=specialist,
                native_key="participants.post", operation_key="", scope="conversation")
        tenant = TenantContext.for_membership(specialist)
        run, _ = execute_action(tenant, "participants.post", {"membership_id": target.pk,
            "reason": "Unauthorized management"}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "failed")
        with tenant_atomic(self.context):
            self.assertFalse(ConversationParticipant.objects.filter(conversation=self.conversation,
                membership=target).exists())
