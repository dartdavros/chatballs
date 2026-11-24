"""A queued replacement of the registered demo, published in one transaction."""

import logging
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.audit_models import AuditResult
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.conflicts import DemoWorkingReference
from chatballs.identity.demo_seed.north_wind.executor_reset import (
    enqueue_executor_reset,
    executor_reset_scope,
)
from chatballs.identity.demo_seed.north_wind.state import initial_state
from chatballs.identity.demo_seed.orchestrator import run_demo_seed
from chatballs.identity.demo_seed.registry import recording, remove_records
from chatballs.identity.demo_seed.service import DemoBusy
from chatballs.identity.event_handlers import DEMO_REINSTALL_REQUESTED
from chatballs.identity.models import HumanUser
from chatballs.tenancy.context import TenantActorKind, TenantContext

logger = logging.getLogger(__name__)


def request_reinstall(*, context, actor, request_id, generation, previous_request_id):
    with transaction.atomic():
        dataset = DemoDataset.objects.select_for_update().filter(
            organization_id=context.organization_id,
        ).first()
        if dataset is None:
            raise ValidationError(t("demo.reinstall_not_installed"))
        if dataset.reinstall_request_id == request_id:
            return
        if dataset.status != DemoDatasetStatus.INSTALLED:
            raise DemoBusy(t("demo.reinstall_unavailable"))
        if dataset.generation != generation or dataset.reinstall_request_id != previous_request_id:
            raise DemoBusy(t("demo.reinstall_stale"))

        dataset.status = DemoDatasetStatus.REINSTALLING
        dataset.requested_by = actor
        dataset.reinstall_request_id = request_id
        dataset.reinstall_finished_at = None
        dataset.reinstall_error = ""
        dataset.save(update_fields=[
            "status", "requested_by", "reinstall_request_id", "reinstall_finished_at", "reinstall_error",
        ])
        _audit(context, dataset, "demo.reinstall_requested", actor_id=actor.pk)
        enqueue_event(DomainEvent(
            aggregate_type="DemoDataset",
            aggregate_id=str(dataset.pk),
            event_type=DEMO_REINSTALL_REQUESTED,
            payload={"datasetId": dataset.pk, "requestId": str(request_id)},
            tenant_context=TenantContext.for_resource(
                context.organization, actor_kind=TenantActorKind.SYSTEM, correlation_id=context.correlation_id,
            ),
        ))


def reinstall(*, context, dataset):
    recorder = None
    error_code = ""
    actor_id = dataset.requested_by_id
    previous_executor = executor_reset_scope(dataset)
    try:
        with transaction.atomic():
            remove_records(dataset)
            dataset.generation = uuid4()
            dataset.shop_state = initial_state()
            dataset.save(update_fields=["generation", "shop_state"])
            with recording(dataset) as recorder:
                run_demo_seed(context, recorder=recorder)
            connection.check_constraints()
            dataset.records_count = dataset.records.count()
    except DemoWorkingReference as error:
        logger.info("Demo reinstallation blocked by %s.%s", error.model_label, error.field)
        error_code = (
            "WORKING_CONVERSATION" if error.model_label == "conversations.conversation"
            else "WORKING_REFERENCE"
        )
    except Exception:  # noqa: BLE001
        logger.exception("Demo reinstallation failed in organization %s", context.organization_id)
        error_code = "PREPARATION_FAILED"

    if error_code:
        if recorder is not None:
            recorder.discard_new_files()
        dataset.refresh_from_db(fields=["generation", "shop_state", "records_count", "finished_at"])
    else:
        dataset.finished_at = timezone.now()
    dataset.reinstall_finished_at = timezone.now()
    dataset.reinstall_error = error_code
    dataset.status = DemoDatasetStatus.INSTALLED
    dataset.save(update_fields=[
        "status", "records_count", "finished_at", "reinstall_finished_at", "reinstall_error",
    ])
    if not error_code:
        enqueue_executor_reset(context, previous_executor)
    _audit(
        context, dataset, "demo.reinstall_failed" if error_code else "demo.reinstalled",
        actor_id=actor_id, error_code=error_code,
    )


def _audit(context, dataset, action, *, actor_id, error_code=""):
    actor = HumanUser.objects.filter(pk=actor_id).first()
    record_audit_event(
        organization=context.organization,
        actor=actor,
        action=action,
        result=AuditResult.FAILED if error_code else AuditResult.SUCCESS,
        object_type="DemoDataset",
        object_id=str(dataset.pk),
        payload={
            "requestId": str(dataset.reinstall_request_id), "errorCode": error_code, "actorUserId": actor_id,
        },
    )
