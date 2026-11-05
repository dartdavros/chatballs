"""Independent extension contract used only by automatic tests; no network server."""

import hashlib
import hmac
import json
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    Delivery,
    Effect,
    EventDescriptor,
    Mode,
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    Presentation,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.adapters.schema import TypeSpec

CALLS = []
VALUE = TypeSpec("object", properties=(("value", TypeSpec("string", required=True)),))


def project(context, operation, arguments):
    CALLS.append((context.connection.pk, context.effect_key, dict(arguments)))
    if arguments["value"] == "fail":
        return OperationResult(ResultState.FAILED, error_code="rejected")
    return OperationResult(ResultState.COMPLETED, data={"value": arguments["value"].upper()})


def pending(context, operation, arguments):
    CALLS.append((context.connection.pk, context.effect_key, dict(arguments)))
    return OperationResult(ResultState.PENDING, correlation=context.effect_key,
        event_key="job.completed", deadline=timezone.now() + timedelta(hours=1))


def resume(context, operation, arguments):
    return OperationResult(ResultState.UNKNOWN)


def ingress(context, body, headers):
    expected = hmac.new(context.credentials["signature"].encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, headers.get("X-Signature", "")):
        raise ValueError("signature")
    data = json.loads(body)
    result = OperationResult(ResultState(data["state"]), data=data["payload"]) if "state" in data else None
    return VerifiedEvent(event_id=data["id"], event_key=data["event"], occurred_at=parse_datetime(data["time"]),
        payload=data["payload"], correlation=data.get("correlation", ""), sequence=data.get("sequence"), result=result)


ADAPTER = AdapterDescriptor(key="independent", contract_version=1, listed=False,
    presentation=Presentation("", "", "", "", "", ""),
    auth_methods=(AuthMethod("token", "bearer@1", "", TypeSpec("object")),),
    operations=(
        OperationDescriptor("project", "runs.operation", Effect.READ, VALUE, VALUE,
            OperationHandlers(execute=project), retry=RetryStrategy.SAFE_READ),
        OperationDescriptor("job", "runs.operation", Effect.READ, VALUE, VALUE,
            OperationHandlers(execute=pending, resume=resume), mode=Mode.LONG, retry=RetryStrategy.SAFE_READ),
    ),
    events=(EventDescriptor("job.completed", "runs.operation", VALUE, Delivery.CALLBACK, ingress=ingress, replay_seconds=86400),),
)
