"""Service connection reads and permission boundary for every product entry."""

from rest_framework.exceptions import PermissionDenied

from chatballs.identity.policy import has_capability_any_scope
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.service_connections.payloads import catalog_payload, connection_payload
from chatballs.tenancy.database import tenant_atomic


def require(context, capability="integrations.view"):
    with tenant_atomic(context):
        if not has_capability_any_scope(context.membership, capability):
            raise PermissionDenied()


def connections(context):
    return Integration.objects.select_related("service_settings").filter(
        organization_id=context.organization_id, provider=IntegrationProvider.ADAPTER)


def load(context, connection_id, capability="integrations.view"):
    require(context, capability)
    with tenant_atomic(context):
        return connections(context).get(pk=connection_id)


def payload(context, integration):
    with tenant_atomic(context):
        return {"connection": connection_payload(integration)}


def listing(context):
    require(context)
    with tenant_atomic(context):
        return {"items": [connection_payload(row) for row in connections(context).order_by("name")]}


def detail(context, connection_id):
    return payload(context, load(context, connection_id))


def adapters(context):
    require(context)
    return {"items": catalog_payload()}

