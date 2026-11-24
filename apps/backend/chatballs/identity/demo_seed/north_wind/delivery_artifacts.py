"""Scope delivery execution artifacts to the provisioned demo instances."""

from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.operation_modes import lock_organization
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.journal import RunJournalEntry
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt
from chatballs.integrations.scenario_state.progress import ScenarioBudget, ScenarioProgress
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep


@contextmanager
def record_native_delivery(tenant, run_id, operation):
    from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
    from chatballs.identity.demo_seed.registry import recording

    if not local_demo_enabled() or operation not in {
        "conversations.priority.post", "conversations.group.post", "conversations.labels.post",
    }:
        yield
        return
    run = ScenarioRun.objects.filter(organization_id=tenant.organization_id, pk=run_id).first()
    dataset = DemoDataset.objects.filter(
        organization_id=tenant.organization_id, status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
    ).first()
    automation = dataset.shop_state.get("deliveryAutomation", {}) if dataset else {}
    if (not run or run.scenario_id not in automation.get("scenarioIds", ())
            or run.conversation_id != automation.get("conversationId")
            or not _demo_revision(automation, run.scenario_id, run.revision)):
        yield
        return
    lock_organization(tenant.organization_id)
    dataset = DemoDataset.objects.select_for_update().get(pk=dataset.pk)
    if dataset.shop_state.get("deliveryAutomation") != automation:
        yield
        return
    with recording(dataset) as recorder:
        before = recorder.sequence
        yield
    if recorder.sequence != before:
        dataset.records_count = dataset.records.count()
        dataset.save(update_fields=["records_count"])


def register_delivery_runs(dataset):
    """Register the runner's rows while deletion owns the generation lock."""
    from chatballs.identity.demo_seed.registry import recording

    automation = dataset.shop_state.get("deliveryAutomation")
    if not automation:
        return
    scenarios = list(ScenarioDefinition.objects.select_for_update().filter(
        organization_id=dataset.organization_id, pk__in=automation["scenarioIds"],
    ).order_by("pk"))
    with recording(dataset) as recorder:
        for scenario in scenarios:
            schedule_id = automation.get("scheduleScenarioId", automation["scenarioIds"][1])
            conversation_id = None if scenario.pk == schedule_id else automation["conversationId"]
            runs = ScenarioRun.objects.select_for_update().filter(
                scenario=scenario, conversation_id=conversation_id, parent__isnull=True,
            ).order_by("pk")
            for run in runs:
                if _demo_revision(automation, scenario.pk, run.revision):
                    register_run(recorder, run)
        step_ids = dataset.records.filter(content_type=ContentType.objects.get_for_model(ScenarioStep)).values_list(
            "object_id", flat=True,
        )
        lanes = ConnectionExecutionLane.objects.filter(integration_id=automation["connectionId"]).filter(
            Q(step__isnull=True) | Q(step_id__in=[int(pk) for pk in step_ids]),
        )
        for lane in lanes:
            _register_once(recorder, lane)


def register_run(recorder, run):
    _register_once(recorder, run)
    steps = ScenarioStep.objects.select_for_update().filter(run=run).order_by("pk")
    for step in steps:
        _register_once(recorder, step)
        for receipt in NativeEffectReceipt.objects.filter(step=step):
            _register_once(recorder, receipt)
    for model, fields in (
        (ScenarioBudget, {"root": run}), (ScenarioProgress, {"run": run}), (RunJournalEntry, {"run": run}),
    ):
        for row in model.objects.filter(**fields):
            _register_once(recorder, row)


def _register_once(recorder, instance):
    content_type = ContentType.objects.get_for_model(instance)
    if not recorder.dataset.records.filter(content_type=content_type, object_id=str(instance.pk)).exists():
        recorder.record(instance)


def _demo_revision(automation, scenario_id, revision):
    revisions = automation.get("scenarioRevisions")
    return revisions is None or revisions.get(str(scenario_id)) == revision
