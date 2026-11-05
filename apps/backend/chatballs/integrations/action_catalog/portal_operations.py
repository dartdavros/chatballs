"""Native portal boundary: canonical tenant, domain policies and safe failures."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.datastructures import MultiValueDict
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as APIValidationError

from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.support_portals.portal_queries import require
from chatballs.support_portals.selectors import portal_articles_queryset, portal_for_context
from chatballs.tenancy.database import tenant_atomic


def parameters(values):
    return MultiValueDict({key: value if isinstance(value, list) else [value] for key, value in values.items()})


def invoke(context, values, *, service, capability):
    with tenant_atomic(context.tenant):
        try:
            if capability:
                require(context.tenant, capability)
            result = service(context, values)
        except (ObjectDoesNotExist, PermissionDenied):
            raise NativeAccessDenied("context") from None
        except (ValidationError, APIValidationError):
            raise NativeOperationRejected("arguments") from None
    return result if isinstance(result, OperationResult) else OperationResult(ResultState.COMPLETED, json_data(result))


def portal(context, values):
    return portal_for_context(context.tenant, values["portal_id"])


def article(context, values):
    return portal_articles_queryset(portal(context, values), MultiValueDict()).get(id=values["article_id"])


def settings(context, values, *, service, by_id=False, body=False, query=False):
    args = [context.tenant]
    if by_id:
        args.append(values["portal_id"])
    if body or query:
        args.append(parameters(values) if query else values)
    return service(*args)
