"""Quality actions run with original version, evidence and supervision checks."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.utils import timezone

from chatballs.conversations.comment_services import create_comment
from chatballs.conversations.comment_test_base import CommentTransactionTestBase
from chatballs.conversations.domain_events import record_fact
from chatballs.conversations.models import Message
from chatballs.conversations.quality.criteria import configure_quality
from chatballs.conversations.quality.jobs import finish_quality_job, start_quality_job
from chatballs.conversations.quality.models import QualityJob, QualitySettings
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.supervision_models import EmployeeGroupSupervision
from chatballs.integrations.action_catalog.testing import execute_action
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.scenario_state.grants import ActionGrant
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class NativeQualityTests(CommentTransactionTestBase):
    def setUp(self):
        super().setUp()
        from chatballs.integrations.adapters.schema import validate_value
        from chatballs.integrations.execution import native
        original = native._result
        self.contract_issues = []
        def checked(action, result):
            self.contract_issues.extend(validate_value(action.operation.output, result.data))
            return original(action, result)
        self.addCleanup(lambda: self.assertEqual(self.contract_issues, []))
        self.enterContext(patch.object(native, "_result", side_effect=checked))

    def test_mixed_scale_preserves_types_and_replay_does_not_create_a_version(self):
        values = {"enabled": True, "criteria": [{"code": "resolution", "description": "Resolution",
            "scale": [{"integerValue": 1}, {"numberValue": 1}, {"textValue": "resolved"}]}]}
        run, result = execute_action(self.context, "quality.settings.put", values)
        self.assertEqual(run.state, "completed")
        self.assertEqual(result["criteria"][0]["scale"], values["criteria"][0]["scale"])
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            settings = QualitySettings.objects.get(organization=self.organization)
            self.assertEqual(settings.current_version.version, 1)
            scale = settings.current_version.criteria[0]["scale"]
            self.assertEqual([type(value) for value in scale], [int, float, str])
        _, result = execute_action(self.context, "quality.settings.get", {})
        self.assertEqual(result["criteriaVersion"], 1)
        values["criteria"][0]["reporting"] = {"positiveValue": "resolved"}
        denied, _ = execute_action(self.context, "quality.settings.put", values)
        self.assertEqual(denied.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(QualitySettings.objects.get().current_version.version, 1)

    def analyzed_job(self, *, criteria=None, value=1, with_operator=False):
        with tenant_atomic(self.context):
            configure_quality(context=self.context, enabled=True,
                criteria=criteria or [{"code": "resolution", "description": "Resolution", "scale": [0, 1, 2]}])
            message = Message.objects.create(conversation=self.conversation, author_type="CONTACT", text="Public question")
            if with_operator:
                Message.objects.create(conversation=self.conversation, author_type="OPERATOR",
                    author_user=self.context.actor_user, text="Employee answer")
            create_comment(context=self.context, conversation_id=self.conversation.pk,
                audience="INTERNAL", text="Private review", operation_id=uuid4())
            self.conversation.lifecycle = "CLOSED"
            self.conversation.save(update_fields=["lifecycle"])
            event = record_fact(self.conversation, "CLOSED")
            job = QualityJob.objects.get(completion_event_id=event.operation_id)
            start_quality_job(context=self.context, job_id=job.pk)
            finish_quality_job(context=self.context, job_id=job.pk, validated_result={"conclusions": [
                {"code": "resolution", "value": value, "explanation": "Explained", "recommendations": [], "messageIds": [message.pk]}]})
        return job, message

    def test_support_feedback_retains_mixed_scales_corrections_and_employee_attribution(self):
        job, _ = self.analyzed_job(criteria=[{"code": "resolution", "description": "Resolution",
            "scale": [1, 1.0, "resolved"]}],
            value=1.0, with_operator=True)
        changed, _ = execute_action(self.context, "quality.correction.post", {"job_id": job.pk,
            "expectedRevision": 0, "criterionCode": "resolution", "scaleIndex": 2, "reason": "Reviewed"})
        self.assertEqual(changed.state, "completed")
        run, result = execute_action(self.context, "reports.support.get", {
            "from": (self.conversation.created_at - timedelta(seconds=1)).isoformat(),
            "to": (timezone.now() + timedelta(seconds=1)).isoformat(), "timezone": "UTC"})
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        quality = result["qualityAnalysis"]
        self.assertEqual(quality["count"], 1)
        self.assertEqual(quality["details"][0]["conclusions"][0]["originalValue"], {"numberValue": 1.0})
        self.assertEqual(quality["details"][0]["conclusions"][0]["effectiveValue"], {"textValue": "resolved"})
        self.assertEqual(quality["groups"][0]["scale"],
            [{"integerValue": 1}, {"numberValue": 1.0}, {"textValue": "resolved"}])
        criterion = quality["versions"][0]["criteria"][0]
        self.assertEqual(criterion["originalSummary"], {"kind": "unavailable", "value": None})
        self.assertEqual(criterion["effectiveSummary"], {"kind": "unavailable", "value": None})
        employee = next(row for row in result["employees"] if row["employee"] == self.context.actor_user.pk)
        self.assertEqual(employee["qualityAnalysis"]["count"], 1)

    def test_support_feedback_preserves_declared_binary_positive_rate(self):
        job, _ = self.analyzed_job(criteria=[{"code": "resolution", "description": "Resolution",
            "scale": ["Yes", "No"], "reporting": {"positiveValue": "Yes"}}], value="Yes")
        changed, _ = execute_action(self.context, "quality.correction.post", {"job_id": job.pk,
            "expectedRevision": 0, "criterionCode": "resolution", "scaleIndex": 1, "reason": "Reviewed"})
        self.assertEqual(changed.state, "completed")
        run, result = execute_action(self.context, "reports.support.get", {
            "from": (self.conversation.created_at - timedelta(seconds=1)).isoformat(),
            "to": (timezone.now() + timedelta(seconds=1)).isoformat(), "timezone": "UTC"})
        self.assertEqual(run.state, "completed", run.steps.get().error_code)
        criterion = result["qualityAnalysis"]["versions"][0]["criteria"][0]
        self.assertEqual(criterion["originalSummary"], {"kind": "positiveRate",
            "positiveValue": {"textValue": "Yes"}, "value": 1})
        self.assertEqual(criterion["effectiveSummary"], {"kind": "positiveRate",
            "positiveValue": {"textValue": "Yes"}, "value": 0})

    def test_review_keeps_original_and_rejects_stale_revision_and_foreign_evidence(self):
        job, message = self.analyzed_job()
        args = {"job_id": job.pk, "expectedRevision": 0, "criterionCode": "resolution", "scaleIndex": 2, "reason": "Reviewed"}
        run, result = execute_action(self.context, "quality.correction.post", args)
        self.assertEqual(run.state, "completed")
        self.assertEqual(result["conclusions"][0]["originalValue"], {"integerValue": 1})
        self.assertEqual(result["conclusions"][0]["effectiveValue"], {"integerValue": 2})
        run_one(self.context, run.public_id)
        stale, _ = execute_action(self.context, "quality.correction.post", args)
        self.assertEqual(stale.state, "failed")
        with tenant_atomic(self.context):
            self.assertEqual(job.result.corrections.count(), 1)
        with tenant_atomic(self.foreign.pk):
            foreign = Message.objects.create(conversation=self.foreign_conversation, author_type="CONTACT", text="Foreign")
        run, result = execute_action(self.context, "quality.evidence.get", {"job_id": job.pk, "message_id": message.pk})
        self.assertEqual((run.state, result["text"]), ("completed", "Public question"))
        run, _ = execute_action(self.context, "quality.evidence.get", {"job_id": job.pk, "message_id": foreign.pk})
        self.assertEqual(run.state, "failed")

    def test_supervision_revocation_and_employee_grant_cannot_bypass_management_scope(self):
        job, _ = self.analyzed_job()
        user = HumanUser.objects.create_user(email="native-quality@tests.local")
        member = OrganizationMembership.objects.create(organization=self.organization, user=user, role="SUPERVISOR")
        context = TenantContext.for_membership(member)
        with tenant_atomic(self.context):
            group = EmployeeGroup.objects.create(organization=self.organization, name="Supervised")
            self.conversation.group = group
            self.conversation.save(update_fields=["group"])
            supervision = EmployeeGroupSupervision.objects.create(organization=self.organization, group=group, employee=member)
            ActionGrant.objects.create(organization=self.organization, membership=member,
                native_key="quality.job.get", scope="organization")
        run, _ = execute_action(context, "quality.job.get", {"job_id": job.pk})
        self.assertEqual(run.state, "completed")
        with tenant_atomic(context):
            supervision.delete()
        run, _ = execute_action(context, "quality.job.get", {"job_id": job.pk})
        self.assertEqual(run.state, "failed")
        OrganizationMembership.objects.filter(pk=member.pk).update(role="EMPLOYEE")
        run, _ = execute_action(context, "quality.job.get", {"job_id": job.pk})
        self.assertEqual(run.state, "failed")

    def test_launch_reports_queued_analysis_and_requires_real_completion_history(self):
        job, _ = self.analyzed_job()
        run, result = execute_action(self.context, "quality.analysis.post",
            {"repeat": True}, conversation_id=self.conversation.pk)
        self.assertEqual(run.state, "completed")
        self.assertEqual(result["state"], "WAITING")
        self.assertEqual(result["revision"], job.revision + 1)
        self.assertEqual(result["conclusions"], [])
        run_one(self.context, run.public_id)
        with tenant_atomic(self.context):
            self.assertEqual(QualityJob.objects.filter(organization=self.organization).count(), 2)
        with tenant_atomic(self.context):
            missing = self.make_conversation(self.organization, "no-completion")
            missing.lifecycle = "CLOSED"
            missing.save(update_fields=["lifecycle"])
        run, _ = execute_action(self.context, "quality.analysis.post", {}, conversation_id=missing.pk)
        self.assertEqual(run.state, "failed")
