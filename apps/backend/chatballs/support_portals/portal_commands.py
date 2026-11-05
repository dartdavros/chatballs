"""Portal commands preserve domain validation and product audit events."""

from chatballs.identity.audit import record_audit_event
from chatballs.support_portals.domain_services import set_custom_domain, verify_custom_domain
from chatballs.support_portals.portal_inputs import portal_input
from chatballs.support_portals.portal_queries import require
from chatballs.support_portals.portal_services import (
    create_portal,
    set_portal_status,
    update_portal,
)
from chatballs.support_portals.selectors import portal_for_context
from chatballs.support_portals.serializers import portal_payload


def _payload(context, portal):
    return {"portal": portal_payload(portal_for_context(context, portal.id))}


def _audit(context, portal, action, request):
    record_audit_event(action=action, actor=context.actor_user, organization=context.organization,
        object_type="SupportPortal", object_id=str(portal.public_id), request=request)


def create(context, body, *, request=None):
    require(context, "support.operate")
    portal = create_portal(context=context, data=portal_input(body))
    _audit(context, portal, "support_portal.created", request)
    return _payload(context, portal)


def update(context, portal_id, body):
    require(context, "support.operate")
    portal = portal_for_context(context, portal_id)
    update_portal(context=context, portal=portal, data=portal_input(body, portal))
    return _payload(context, portal)


def status(context, portal_id, body, *, request=None):
    require(context, "support.operate")
    portal = set_portal_status(context=context, portal=portal_for_context(context, portal_id),
        status=str(body.get("status", "")))
    _audit(context, portal, f"support_portal.{portal.status.lower()}", request)
    return _payload(context, portal)


def domain(context, portal_id, body):
    require(context, "support.operate")
    portal = set_custom_domain(portal_for_context(context, portal_id), str(body.get("customDomain", "")))
    return _payload(context, portal)


def verify_domain(context, portal_id):
    require(context, "support.operate")
    portal = verify_custom_domain(portal_for_context(context, portal_id))
    return _payload(context, portal)
