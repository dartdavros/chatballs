"""Provisioning is executable only with the existing platform token capability."""

from rest_framework.exceptions import PermissionDenied

from chatballs.integrations.action_catalog.authority import require_context
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.profile_schemas import field
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import validate_value
from chatballs.platform import commands

INPUT = obj(name=field("name", required=True), slug=field("slug", required=True),
    owner_email=field("ownerEmail", required=True), timezone=field("timezone", required=True),
    locale=field("language"), legal_name=field("legalName"), tax_profile=field("taxProfile", "object", open=True, nullable=True),
    idempotencyKey=field("idempotencyKey", required=True))
OUTPUT = obj(organization=obj(publicId=field("organizationPublicId"), name=field("name"),
    slug=field("slug"), status=field("status"), timezone=field("timezone")),
    provisioning=obj(status=field("status"), source=field("source"), idempotencyKey=field("idempotencyKey")),
    owner=obj(state=field("status")))


def provision(context, values):
    require_context(context, "platform")
    if validate_value(INPUT, values):
        raise NativeOperationRejected("arguments")
    body = {key: value for key, value in values.items() if key != "idempotencyKey"}
    try:
        outcome = commands.provision(context.user, context.token, body, idempotency_key=values["idempotencyKey"])
    except PermissionDenied:
        raise NativeAccessDenied("permission") from None
    if outcome.status >= 400:
        raise NativeOperationRejected("operation_rejected")
    return OperationResult(ResultState.COMPLETED, outcome.data)


action(key="platform.organizations.provision", title="native.platform.organizations.provision", input=INPUT, output=OUTPUT,
    handler=provision, capability="platform.organizations.provision", scope="platform", authority="platform", surface="platform",
    route="api/v1/organizations", view="chatballs.platform.views.OrganizationProvisionView", method="POST", effect=Effect.CREATE)
