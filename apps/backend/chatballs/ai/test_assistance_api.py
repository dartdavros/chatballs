from uuid import uuid4

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from chatballs.ai.assistance_behavior_base import AssistanceBehaviorData
from chatballs.ai.assistance_services import ASSISTANCE_REQUESTED
from chatballs.ai.assistance_views import (
    AssistanceDetailView,
    AssistanceListView,
    AssistanceRejectView,
)
from chatballs.ai.models import ReplyAssistanceAttempt, ReplySuggestion
from chatballs.conversations.models import Conversation
from chatballs.events.models import OutboxEvent
from chatballs.identity.models import EmployeeRole, HumanUser, OrganizationMembership
from chatballs.tenancy.context import TenantContext


class AssistanceApiTests(AssistanceBehaviorData, TestCase):
    def api(self, view, method="post", data=None, context=None, **kwargs):
        context = context or self.context
        request = getattr(APIRequestFactory(), method)("/", data or {}, format="json")
        request.tenant_context = context
        force_authenticate(request, context.actor_user)
        return view.as_view()(request, conversation_id=self.conversation.pk, **kwargs)

    def test_idempotency_alternative_and_rejection_preserve_each_source_and_author(self):
        response = self.api(AssistanceListView, data={"operationKey": "first"})
        self.assertEqual(response.status_code, 202)
        repeated = self.api(AssistanceListView, data={"operationKey": "first"})
        self.assertEqual(response.data, repeated.data)
        requested = OutboxEvent.objects.filter(event_type=ASSISTANCE_REQUESTED)
        self.assertEqual(requested.count(), 1)
        self.assertEqual(requested.get().payload["suggestionId"], response.data["suggestion"]["id"])
        original = self.generate(ReplySuggestion.objects.get())
        alternative = self.api(AssistanceListView, data={
            "operationKey": "alternative", "attemptId": str(original.attempt.public_id),
        })
        self.assertEqual(alternative.status_code, 202)
        second = self.generate(ReplySuggestion.objects.get(position=2))
        rejected = self.api(AssistanceRejectView, suggestion_id=original.public_id)
        self.assertEqual(rejected.status_code, 200)
        original.refresh_from_db()
        self.assertEqual(original.rejected_by, self.member)
        self.assertIsNotNone(original.rejected_at)
        self.assertTrue(original.original_text)
        self.assertTrue(second.original_text)
        detail = self.api(AssistanceDetailView, "get", attempt_id=original.attempt.public_id)
        self.assertEqual(len(detail.data["attempt"]["suggestions"]), 2)
        self.assertEqual(second.requested_by, self.member)

    def test_read_visibility_does_not_grant_reply_and_revocation_hides_results(self):
        user = HumanUser.objects.create_user(email="viewer@example.test")
        member = OrganizationMembership.objects.create(
            organization=self.organization, user=user, role=EmployeeRole.EMPLOYEE,
        )
        context = TenantContext.for_membership(member)
        suggestion = self.generate(self.request())
        for view, method, kwargs in (
            (AssistanceListView, "post", {}),
            (AssistanceDetailView, "get", {"attempt_id": suggestion.attempt.public_id}),
            (AssistanceRejectView, "post", {"suggestion_id": suggestion.public_id}),
        ):
            response = self.api(view, method, data={"operationKey": "viewer"},
                                context=context, **kwargs)
            self.assertEqual(response.status_code, 403)
        self.member.blocked_at = timezone.now()
        self.member.save(update_fields=["blocked_at"])
        self.assertEqual(self.api(AssistanceDetailView, "get",
                         attempt_id=suggestion.attempt.public_id).status_code, 403)

    def test_foreign_attempt_closed_dialog_and_invalid_key_are_rejected(self):
        other, member, agent, conversation = self.create_tenant("other")
        foreign = ReplyAssistanceAttempt.objects.create(
            organization=other, requested_by=member, conversation=conversation, agent=agent,
            operation_key="foreign", history_version="v1",
        )
        response = self.api(AssistanceListView, data={
            "operationKey": "alt", "attemptId": str(foreign.public_id),
        })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.api(AssistanceDetailView, "get", attempt_id=uuid4()).status_code, 404)
        for key in ("", "x" * 161):
            self.assertEqual(self.api(AssistanceListView, data={"operationKey": key}).status_code, 400)
        Conversation.objects.filter(pk=self.conversation.pk).update(lifecycle="CLOSED")
        self.assertEqual(self.api(AssistanceListView, data={"operationKey": "closed"}).status_code, 400)
        self.assertFalse(ReplySuggestion.objects.exists())

    def test_protected_read_expires_abandoned_work_without_generation(self):
        suggestion = self.request()
        with override_settings(CHATBALLS_AI_TURN_DEADLINE_SECONDS=-1):
            response = self.api(AssistanceDetailView, "get", attempt_id=suggestion.attempt.public_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["attempt"]["status"], "ERROR")
        self.assertEqual(response.data["attempt"]["suggestions"][0]["errorCode"], "TIMEOUT")
        self.generate(suggestion)
        self.assertEqual(suggestion.original_text, "")
