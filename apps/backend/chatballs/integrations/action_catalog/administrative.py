"""Global descriptors call domain commands without a synthetic tenant or request."""

from functools import partial

from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied

from chatballs.integrations.action_catalog.authority import require_context
from chatballs.integrations.action_catalog.contracts import (
    APIEntry,
    NativeAccessDenied,
    NativeAction,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.registry import register_action
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import (
    OperationDescriptor,
    OperationHandlers,
    OperationResult,
    ResultState,
)
from chatballs.integrations.adapters.schema import validate_value


def invoke(context, values, *, authority, inputs, service, body, audit, project):
    require_context(context, authority)
    if validate_value(inputs, values):
        raise NativeOperationRejected("arguments")
    args = [context.user, values] if body else [context.user]
    try:
        outcome = service(*args, **({"request": context.request} if audit else {}))
    except PermissionDenied:
        raise NativeAccessDenied("permission") from None
    except ValidationError:
        raise NativeOperationRejected("arguments") from None
    if outcome.status >= 400:
        raise NativeOperationRejected("operation_rejected")
    data = json_data(outcome.data)
    return OperationResult(ResultState.COMPLETED, project(data) if project else data)


def register(*, key, inputs, outputs, service, route, view, method, effect,
             authority="instance", execution="local", body=False, audit=False, project=None):
    operation = OperationDescriptor(key=key, title_key=f"native.{key}", input=inputs,
        output=outputs, effect=effect, handlers=OperationHandlers(), permission_scope=authority)
    return register_action(NativeAction(operation=operation,
        execute=partial(invoke, authority=authority, inputs=inputs, service=service,
            body=body, audit=audit, project=project), capability="", scope=authority,
        entries=(APIEntry(route, method, view),), execution=execution, authority=authority))
