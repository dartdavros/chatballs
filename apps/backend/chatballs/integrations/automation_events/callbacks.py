"""Resume exact tenant/connection waits; duplicate jobs are harmless."""

from django.utils import timezone

from chatballs.events.handlers import register
from chatballs.integrations.adapters.contracts import ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.integrations.execution.actions import resolve_action
from chatballs.integrations.execution.block_values import actual
from chatballs.integrations.execution.budgets import lock_run
from chatballs.integrations.execution.conditions import evaluate_conditions
from chatballs.integrations.execution.events import schedule
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.integrations.scenario_state.waits import ScenarioWait
from chatballs.tenancy.database import tenant_atomic


def match_wait(tenant, wait, *, registry=None):
    if wait.state != "pending" or wait.kind not in {"event", "reply", "operation"}:
        return
    rows = EventReceipt.objects.filter(organization_id=wait.organization_id,
        integration_id=wait.integration_id, event_key=wait.event_key, cleared_at__isnull=True,
        expires_at__gt=timezone.now(), occurred_at__lte=wait.deadline).order_by("received_at", "pk")
    if wait.kind == "operation":
        from django.db.models import F
        rows = rows.filter(correlation_hash=wait.correlation_hash).order_by(F("sequence").desc(nulls_last=True), "pk")
    else:
        # An event may arrive before registration, but never before the Run.
        rows = rows.filter(occurred_at__gte=wait.run.created_at)
    data = wait.definition
    if wait.kind != "operation":
        rows = rows.filter(pk__gt=data.get("receiptCursor", 0)).order_by("pk")
    batch = list(rows[:100])
    for receipt in batch:
        if wait.kind != "operation":
            data["receiptCursor"] = receipt.pk
        content = receipt.definition
        if wait.kind == "reply":
            if content["payload"].get("conversationId") != wait.run.conversation_id:
                continue
        if wait.kind == "event":
            values = actual(tenant, wait.run, data["values"])
            values.event = content["payload"]
            if not evaluate_conditions({"conditions": data["block"]["condition"]}, wait.run.conversation,
                    values.parameters, values=values, registry=registry):
                continue
        if wait.kind == "operation":
            if not content.get("result") or receipt.scenariowait_set.exclude(pk=wait.pk).exists():
                continue
            step = wait.run.steps.select_for_update().get(path=wait.path)
            result = content["result"]
            try:
                state = ResultState(result["state"])
            except (KeyError, ValueError):
                continue
            if state not in {ResultState.COMPLETED, ResultState.FAILED, ResultState.UNKNOWN}:
                continue
            _, _, adapter, _, operation = resolve_action(tenant.organization_id, step.integration_id,
                f"service:{step.operation_key}", expected=(step.adapter_key, step.adapter_version),
                registry=registry, recovering=True)
            if wait.run.definition.get("composite"):
                from chatballs.integrations.execution.snapshots import check_contract
                check_contract(wait.run, {"connection": str(step.integration_id),
                    "target": f"service:{step.operation_key}"}, operation, adapter)
            if state == ResultState.COMPLETED and validate_value(operation.output, result.get("data")):
                continue
            from chatballs.integrations.execution.checkpoints import finish
            data = step.definition
            data["result"] = result.get("data")
            step.definition = data
            finish(wait.run, step, state.value, code="" if state == ResultState.COMPLETED else "operation_rejected")
        wait.receipt = receipt
        wait.state = "completed"
        wait.save(update_fields=["receipt", "state"])
        wait.run.progress.filter(path=wait.path).update(state="queued")
        schedule(tenant, wait.run)
        return
    if wait.kind != "operation" and batch:
        wait.definition = data
        wait.save(update_fields=["content"])
        if len(batch) == 100:
            wait.run.progress.filter(path=wait.path).update(state="queued")
            schedule(tenant, wait.run)


@register("integrations.receipt", manages_own_transaction=True)
def deliver(payload, tenant):
    with tenant_atomic(tenant):
        receipt = EventReceipt.objects.get(pk=payload["receiptId"], organization_id=tenant.organization_id)
        ids = list(ScenarioWait.objects.filter(organization_id=tenant.organization_id, state="pending",
            integration_id=receipt.integration_id, event_key=receipt.event_key,
            pk__gt=payload.get("afterWaitId", 0)).order_by("pk").values_list("pk", flat=True)[:50])
    for pk in ids:
        with tenant_atomic(tenant):
            row = ScenarioWait.objects.get(pk=pk)
            lock_run(tenant, pk=row.run_id)
            row = ScenarioWait.objects.select_for_update().get(pk=pk)
            match_wait(tenant, row)
    if len(ids) == 50:
        from chatballs.events.services import DomainEvent, enqueue_event
        from chatballs.integrations.execution.events import system_context
        with tenant_atomic(tenant):
            enqueue_event(DomainEvent(aggregate_type="service_receipt", aggregate_id=str(receipt.pk),
                event_type="integrations.receipt", payload={"receiptId": receipt.pk, "afterWaitId": ids[-1]},
                tenant_context=system_context(tenant)))
