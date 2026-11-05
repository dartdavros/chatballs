"""Bounded cleanup protects unfinished/recovering runs and independent files."""

from datetime import timedelta

from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.events import system_context
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.scenario_state.files import ServiceFile
from chatballs.integrations.scenario_state.retention import ScenarioRetentionPolicy
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.storage import adjust_storage_usage


def policy_for(tenant):
    row, _ = ScenarioRetentionPolicy.objects.get_or_create(organization_id=tenant.organization_id)
    return row


def update_policy(tenant, *, step_days, journal_days, version, confirmed=False):
    if any(type(value) is not int or not 1 <= value <= 3650 for value in (step_days, journal_days)) or step_days > journal_days:
        raise ExecutionDenied("retention_values")
    with tenant_atomic(tenant):
        tenant = current_actor(tenant)
        if tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")
        policy_for(tenant)
        row = ScenarioRetentionPolicy.objects.select_for_update().get(organization_id=tenant.organization_id)
        if row.version != version:
            raise ExecutionDenied("state_changed")
        old_step, old_journal = effective_days(row)
        shortening = step_days < old_step or journal_days < old_journal
        if shortening and confirmed is not True:
            raise ExecutionDenied("retention_confirmation")
        row.previous_step_days, row.previous_journal_days = old_step, old_journal
        row.step_days, row.journal_days = step_days, journal_days
        row.effective_at = timezone.now() + timedelta(hours=24) if shortening else None
        row.version += 1
        row.save()
        record_audit_event(action="integrations.retention_changed", actor=tenant.actor_user,
            organization=tenant.organization, object_type="ScenarioRetentionPolicy", object_id=str(row.pk),
            payload={"stepDays": step_days, "journalDays": journal_days, "version": row.version})
        return row


def effective_days(row, now=None):
    now = now or timezone.now()
    if row.effective_at and row.effective_at > now:
        # Increases apply immediately; a pending decrease never postpones
        # ordinary cleanup under the previous policy.
        return max(row.step_days, row.previous_step_days), max(row.journal_days, row.previous_journal_days)
    return row.step_days, row.journal_days


def _delete_orphan_files(tenant, step_ids):
    from chatballs.integrations.scenario_state.retention import StepOperationalFile
    StepOperationalFile.objects.filter(step_id__in=step_ids).delete()
    # Include files left behind by a previous failed storage deletion. The row
    # survives until the physical object has actually been removed.
    files = ServiceFile.objects.filter(organization_id=tenant.organization_id,
        independent_owner=False, execution_owners__isnull=True).order_by("pk")[:25]
    for file in files:
        enqueue_event(DomainEvent(aggregate_type="service_file", aggregate_id=str(file.public_id),
            event_type="integrations.delete_operation_file", payload={"fileId": str(file.public_id)},
            tenant_context=system_context(tenant)))


@register("integrations.delete_operation_file")
def delete_operation_file(payload, tenant):
    if tenant is None:
        raise ValueError("File cleanup requires tenant")
    record = ServiceFile.objects.select_for_update().filter(organization_id=tenant.organization_id,
        public_id=payload["fileId"], independent_owner=False).first()
    if record is None or record.execution_owners.exists():
        return
    # Storage.delete is idempotent. On storage/DB failure the row/outbox remain
    # recoverable; quota is released only with successful row deletion.
    try:
        record.file.delete(save=False)
    except Exception:
        raise RuntimeError("operation_file_cleanup_failed") from None
    adjust_storage_usage(context=tenant, delta_bytes=-record.size)
    record.delete()


def cleanup(tenant, *, limit=50):
    now = timezone.now()
    with tenant_atomic(tenant):
        days, history = effective_days(policy_for(tenant), now)
        runs = ScenarioRun.objects.select_for_update(skip_locked=True).filter(
            organization_id=tenant.organization_id, finished_at__isnull=False,
            finished_at__lte=now - timedelta(days=days), data_cleared_at__isnull=True,
        ).order_by("finished_at")[:limit]
        count = 0
        cleared_step_ids = []
        for run in runs:
            if run.children.filter(finished_at__isnull=True).exists() or run.waits.filter(state="pending").exists():
                continue
            if run.parent_id and run.parent.finished_at is None:
                continue
            step_ids = list(run.steps.values_list("pk", flat=True))
            cleared_step_ids.extend(step_ids)
            run.steps.update(content="", confirmed_digest="", approval_expires_at=None)
            from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
            NativeEffectReceipt.objects.filter(step_id__in=step_ids).delete()
            run.progress.update(content="")
            run.waits.update(content="")
            run.content = ""
            run.data_cleared_at = now
            run.save(update_fields=["content", "data_cleared_at"])
            count += 1
        expired = ScenarioRun.objects.select_for_update(skip_locked=True).filter(
            organization_id=tenant.organization_id, finished_at__lte=now - timedelta(days=history),
            data_cleared_at__isnull=False, journal_cleared_at__isnull=True,
        ).order_by("finished_at")[:limit]
        for run in expired:
            run.journal.all().delete()
            run.steps.all().delete()
            run.progress.all().delete()
            run.waits.all().delete()
            run.structure = {}
            run.initiator_id = None
            run.conversation_id = None
            run.scenario_id = None
            run.journal_cleared_at = now
            run.save(update_fields=["journal_cleared_at", "structure", "initiator", "conversation", "scenario"])
        _delete_orphan_files(tenant, cleared_step_ids)
        from chatballs.integrations.automation_events.retention import cleanup_receipts
        cleanup_receipts(tenant, now=now)
        from chatballs.integrations.scenarios.synchronization_retention import clear_inactive
        clear_inactive(tenant, now=now, days=days)
        return count
