"""Consent-bound native ingress; shared receipt/outbox commits before the view ACK."""

import hashlib
import json

from django.utils import timezone

from chatballs.ai.execution_version import configuration_version
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.integrations.adapters.events import VerifiedEvent
from chatballs.integrations.automation_events.ingress import persist
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.consent import require_current_consent
from chatballs.webchat.models import WebSession
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_config import EVENT_KEY, configured_scenario
from chatballs.webchat.site_event_schema import reject, validate_data, validate_envelope


def digest_rule(rule):
    return hashlib.sha256(json.dumps(rule, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def receive(tenant, session, envelope, *, origin):
    from chatballs.webchat.proactive_guards import available_session, has_history

    validate_envelope(envelope)
    with tenant_atomic(tenant):
        organization = lock_organization(tenant.organization_id)
        Integration.objects.select_for_update().get(pk=session.connection_id, organization=organization)
        session = WebSession.objects.select_for_update(of=("self",)).select_related(
            "widget", "connection__channel__ai_agent", "identity").get(pk=session.pk, organization=organization)
        if not available_session(session, origin):
            raise ExecutionDenied("permission")
        require_current_consent(session)
        rule = session.connection.config.get("siteEvent")
        if not rule or not rule["active"] or envelope["name"] != rule["name"]:
            reject()
        validate_data(rule["schema"], envelope["data"])
        scenario = configured_scenario(session.connection)
        existing = SiteEventLaunch.objects.filter(session=session, rule_id=rule["id"]).first()
        if existing:
            return existing, False
        if not scenario.enabled or has_history(session) or not autonomous_allowed(
                session.connection.channel, organization=organization, connection=session.connection):
            raise ExecutionDenied("site_event_suppressed")
        agent = session.connection.channel.ai_agent
        claim = SiteEventLaunch.objects.create(organization=organization, session=session,
            rule_id=rule["id"], rule_digest=digest_rule(rule), origin=origin,
            mode_version=organization.operation_mode_version, agent_id_snapshot=agent.pk,
            agent_version=configuration_version(agent))
        event_id = f"site:{session.widget_id}:{session.pk}:{rule['id']}:{envelope['eventId']}"
        receipt, _ = persist(tenant, None, VerifiedEvent(event_id=event_id, event_key=EVENT_KEY,
            occurred_at=timezone.now(), payload={"launchId": claim.pk, "name": envelope["name"], "data": envelope["data"]}),
            replay_seconds=30 * 86400, audience=scenario.pk)
        claim.receipt = receipt
        claim.save(update_fields=["receipt"])
        return claim, True
