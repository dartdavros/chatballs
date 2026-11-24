"""Service contract for the private North Wind carrier."""

import hashlib
import hmac
import json
from datetime import timedelta
from http.client import HTTPException

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.local_transport import (
    HTTP_DELIVERY_CHECK_URL,
    HTTP_DELIVERY_HEALTH_URL,
    HTTP_DELIVERY_RESULT_URL,
    HTTP_ORDER_URL,
)
from chatballs.integrations import tool_client
from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    Delivery,
    Effect,
    EntityDescriptor,
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
from chatballs.integrations.tool_network import ToolAddressRejected

EVENT = "delivery.delayed"
ENTITY = "shipment"
HEADER = "X-North-Wind-Signature"
REPLAY_SECONDS = 86400
ORDER_NUMBER = 2043
_INPUT = TypeSpec("object", properties=(("order_number", TypeSpec("integer", required=True)),))
_OUTPUT = TypeSpec("object", properties=(
    ("number", TypeSpec("integer", required=True)),
    ("status", TypeSpec("string", required=True)),
    ("confirmedEta", TypeSpec("boolean", required=True)),
    ("needsAttention", TypeSpec("boolean", required=True)),
    ("eta", TypeSpec("string")),
))
_EVENT_PAYLOAD = TypeSpec("object", properties=(("orderNumber", TypeSpec("integer", required=True)),))


def sign(secret, body):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_delivery_service(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = tool_client.fetch(HTTP_DELIVERY_HEALTH_URL, method="POST", timeout=5, headers=headers)
        if response.status == 200 and json.loads(response.body) == {"ready": True}:
            return
    except (HTTPException, OSError, ToolAddressRejected, tool_client.ToolResponseRejected, ValueError):
        pass
    raise RuntimeError("The local North Wind carrier is unavailable")


def _ingress(context, body, headers):
    supplied = next((value for name, value in headers.items() if name.lower() == HEADER.lower()), "")
    if not local_demo_enabled() or not hmac.compare_digest(sign(context.credentials["signature"], body), supplied):
        raise ValueError("signature")
    event = json.loads(body)
    if event["type"] != EVENT or event["orderNumber"] != ORDER_NUMBER:
        raise ValueError("shipment")
    return VerifiedEvent(
        event_id=event["id"], event_key=EVENT, occurred_at=parse_datetime(event["occurredAt"]),
        payload={"orderNumber": ORDER_NUMBER}, entity_kind=ENTITY, entity_id=str(ORDER_NUMBER),
    )


def _execute(context, operation, arguments):
    url = HTTP_ORDER_URL if operation.effect == Effect.READ else HTTP_DELIVERY_CHECK_URL
    return _request(context, url, arguments)


def _resume(context, operation, arguments):
    return _request(context, HTTP_DELIVERY_RESULT_URL, {"order_number": arguments["order_number"]})


def _request(context, url, arguments):
    if not local_demo_enabled() or arguments["order_number"] != ORDER_NUMBER:
        return OperationResult(ResultState.FAILED, error_code="rejected")
    carrier_check = url != HTTP_ORDER_URL
    headers = {"Authorization": f"Bearer {context.credentials['token']}", "Content-Type": "application/json"}
    if carrier_check:
        headers["Idempotency-Key"] = context.effect_key
    try:
        response = tool_client.fetch(
            url, method="POST", timeout=5, headers=headers, body=json.dumps(arguments).encode(),
        )
        if response.status != 200:
            return OperationResult(ResultState.FAILED, error_code="rejected")
        value = json.loads(response.body)
        if value.get("pending") is True:
            return OperationResult(
                ResultState.PENDING, continuation=arguments, retry_after_seconds=2,
                deadline=timezone.now() + timedelta(minutes=2),
            )
        return OperationResult(ResultState.COMPLETED, data={
            "number": value["number"], "status": value["status"],
            "confirmedEta": value.get("confirmedEta", bool(value.get("eta"))),
            "needsAttention": value["needsAttention"],
            **({"eta": value["eta"]} if value.get("eta") else {}),
        })
    except (HTTPException, OSError, ToolAddressRejected, tool_client.ToolResponseRejected, ValueError, KeyError):
        return OperationResult(ResultState.UNKNOWN if carrier_check else ResultState.FAILED, error_code="unavailable")


ADAPTER = AdapterDescriptor(
    key="north_wind_delivery", contract_version=1, listed=False,
    presentation=Presentation("north_wind.delivery_name", "", "", "", "", ""),
    auth_methods=(AuthMethod("local", "bearer@1", "", TypeSpec("object")),),
    operations=(
        OperationDescriptor("shipment.status", "north_wind.shipment_status", Effect.READ, _INPUT, _OUTPUT,
            OperationHandlers(execute=_execute), retry=RetryStrategy.SAFE_READ),
        OperationDescriptor("delivery.check", "north_wind.delivery_check", Effect.UPDATE, _INPUT, _OUTPUT,
            OperationHandlers(execute=_execute, resume=_resume), mode=Mode.LONG, retry=RetryStrategy.IDEMPOTENCY_KEY),
    ),
    events=(EventDescriptor(EVENT, "north_wind.delivery_delayed", _EVENT_PAYLOAD, Delivery.WEBHOOK,
        ingress=_ingress, replay_seconds=REPLAY_SECONDS),),
    entities=(EntityDescriptor(ENTITY, "north_wind.shipment_status", _OUTPUT, native_entities=("conversation",)),),
)
