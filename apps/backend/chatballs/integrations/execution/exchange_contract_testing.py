"""Independent executable extension for isolated contract tests, never installed."""

from datetime import datetime

from django.utils import timezone

from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    Effect,
    EntityDescriptor,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    Presentation,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.references import EntityReferences, ReferenceCandidate
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.adapters.synchronization import EntitySnapshot, SynchronizationBinding

RECORDS, WRITES, RECEIPTS = {}, [], {}
OBJECT = TypeSpec("object", open=True)
FIELDS = TypeSpec("object", properties=(("displayName", TypeSpec("string", title_key="scenarios.contact_name")),))
IDENTITY = ("id", TypeSpec("string", required=True))


def read(context, operation, arguments):
    return OperationResult(ResultState.COMPLETED, data=dict(RECORDS[arguments["id"]]))


def search(context, operation, arguments):
    query = arguments["query"].casefold()
    return OperationResult(ResultState.COMPLETED, data={"items": [
        {"id": identity, "label": value["displayName"]} for identity, value in RECORDS.items()
        if query in value["displayName"].casefold()]})


def change(context, operation, arguments):
    if context.effect_key in RECEIPTS:
        return RECEIPTS[context.effect_key]
    current = RECORDS[arguments["id"]]
    if str(current["version"]) != arguments["expected"]:
        return OperationResult(ResultState.FAILED, error_code="state_changed")
    current = {**current, **arguments.get("fields", {}), "version": str(int(current["version"]) + 1),
        "modifiedAt": timezone.now().isoformat(), "deleted": operation.key == "remove"}
    RECORDS[arguments["id"]] = current
    WRITES.append((operation.key, arguments["id"], context.effect_key, context.causal_chain))
    result = OperationResult(ResultState.COMPLETED, data={"version": current["version"]})
    RECEIPTS[context.effect_key] = result
    return result


def snapshot(value):
    return EntitySnapshot({"displayName": value.get("displayName", "")}, str(value["version"]),
        datetime.fromisoformat(value["modifiedAt"]), bool(value.get("deleted")))


ADAPTER = AdapterDescriptor("exchange_contract", 1, Presentation("", "", "", "", "", ""),
    (AuthMethod("public", "bearer@1", "", TypeSpec("object")),),
    (OperationDescriptor("search", "runs.synchronization", Effect.READ,
        TypeSpec("object", properties=(("query", TypeSpec("string", required=True)),)), OBJECT,
        OperationHandlers(execute=search), retry=RetryStrategy.SAFE_READ),
     OperationDescriptor("read", "runs.synchronization", Effect.READ, TypeSpec("object", properties=(IDENTITY,)), OBJECT,
        OperationHandlers(execute=read), retry=RetryStrategy.SAFE_READ),
     OperationDescriptor("update", "runs.synchronization", Effect.UPDATE,
        TypeSpec("object", properties=(IDENTITY, ("expected", TypeSpec("string", required=True)), ("fields", TypeSpec("object", open=True, required=True)))), OBJECT,
        OperationHandlers(execute=change, reconcile=change), retry=RetryStrategy.IDEMPOTENCY_KEY),
     OperationDescriptor("remove", "runs.synchronization", Effect.DELETE,
        TypeSpec("object", properties=(IDENTITY, ("expected", TypeSpec("string", required=True)))), OBJECT,
        OperationHandlers(execute=change, reconcile=change), retry=RetryStrategy.IDEMPOTENCY_KEY)),
    entities=(EntityDescriptor("person", "scenarios.contact", FIELDS, native_entities=("contact", "conversation"),
        references=EntityReferences("search", lambda query: {"query": query},
            lambda value: tuple(ReferenceCandidate(item["id"], item["label"]) for item in value["items"])),
        synchronization=SynchronizationBinding("read", lambda identity: {"id": identity}, snapshot,
            "update", lambda identity, fields, version, causal: {"id": identity, "fields": fields, "expected": version},
            "remove", lambda identity, version, causal: {"id": identity, "expected": version})),), listed=False)
