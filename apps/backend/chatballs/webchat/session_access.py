"""Resolve an existing WebSession credential without a synthetic request."""

from contextlib import contextmanager

from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import web_session_route
from chatballs.tenancy.lookup import load_organization
from chatballs.webchat import services


@contextmanager
def resolved_web_session(token, *, expected_organization_id=None):
    route = web_session_route(services.hash_session_token(token)) if token else None
    if route is None or (expected_organization_id is not None
            and route.organization_id != expected_organization_id):
        yield None, None
        return
    organization = load_organization(route.organization_id)
    if organization is None:
        yield None, None
        return
    context = TenantContext.for_resource(organization)
    with tenant_atomic(context):
        session = services.resolve_session(context=context, token=token,
            session_id=int(route.resource_id))
        yield context, session
