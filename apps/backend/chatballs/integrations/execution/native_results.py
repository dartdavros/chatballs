"""Encrypted native receipts retain typed file metadata and execution ownership."""

from dataclasses import asdict

from chatballs.integrations.adapters.contracts import FileRef, OperationResult, ResultState
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.files import file_references
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.files import ServiceFile
from chatballs.integrations.scenario_state.native_receipts import NativeEffectReceipt


def restored(receipt):
    payload = receipt.definition
    return OperationResult(ResultState(payload.get("state", "completed")), payload["result"],
        error_code=payload.get("error_code", ""),
        files=tuple(FileRef(**item) for item in payload.get("files", [])))


def validate_files(action, result, step):
    if result.state == ResultState.FAILED:
        return
    references = file_references(action.operation.output, result.data)
    references.update(str(file.file_id) for file in result.files)
    records = {str(row.public_id): row for row in ServiceFile.objects.filter(
        organization_id=step.organization_id, execution_owners__step=step, public_id__in=references,
    )}
    if set(records) != references:
        raise ExecutionDenied("invalid_result")
    for file in result.files:
        record = records[str(file.file_id)]
        if (file.name != record.name or file.content_type != record.content_type or file.size != record.size
                or file.size > action.operation.limits.max_file_bytes):
            raise ExecutionDenied("invalid_result")


def save(run, step, action, result, *, actor=None):
    validate_files(action, result, step)
    payload = {"state": result.state.value, "error_code": result.error_code,
        "result": result.data, "files": [asdict(file) for file in result.files]}
    existing = NativeEffectReceipt.objects.filter(step=step).first()
    if existing is not None:
        previous = existing.definition
        previous.setdefault("state", ResultState.COMPLETED.value)
        previous.setdefault("error_code", "")
        previous.setdefault("files", [])
        if existing.invocation_digest != invocation_digest(step, run) or previous != payload:
            raise ExecutionDenied("invalid_result")
        return existing
    receipt = NativeEffectReceipt(organization_id=run.organization_id,
        step=step, invocation_digest=invocation_digest(step, run))
    receipt.definition = payload
    receipt.save()
    if actor and run.definition.get("ai") and result.state == ResultState.COMPLETED:
        from chatballs.identity.audit import record_audit_event
        from chatballs.identity.audit_context import native_audit
        with native_audit(run, step, actor, title_key=action.operation.title_key):
            record_audit_event(action="integrations.native_action_executed", organization=actor.organization,
                actor=actor.actor_user, object_type="ScenarioRun", object_id=str(run.public_id))
    return receipt
