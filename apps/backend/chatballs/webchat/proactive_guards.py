"""Revalidate the visitor, current rule and AI generation before each effect."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from chatballs.ai.execution_version import configuration_version
from chatballs.conversations.models import Conversation
from chatballs.identity.operation_modes import autonomous_allowed, lock_organization
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration, IntegrationStatus
from chatballs.webchat.consent import has_current_consent
from chatballs.webchat.models import WebChatWidgetStatus, WebSession
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.sessions import origin_allowed


def available_session(session, origin):
    connection, widget = session.connection, session.widget
    return bool(len(origin) <= 2048 and widget.integration_id == connection.pk
        and widget.organization_id == session.organization_id == connection.organization_id
        and session.identity.connection_id == connection.pk
        and widget.status == WebChatWidgetStatus.PUBLISHED
        and connection.is_active and connection.status == IntegrationStatus.OK
        and connection.channel_id and connection.channel.is_active
        and connection.channel.allow_anonymous_sessions and origin_allowed(widget, origin)
        and session.last_seen_at > timezone.now() - timedelta(seconds=settings.CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS))


def has_history(session):
    return Conversation.objects.filter(organization_id=session.organization_id,
        channel_id=session.connection.channel_id, contact_id=session.identity.contact_id).exists()


def expired(claim):
    return timezone.now() > claim.created_at + timedelta(seconds=settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS)


def for_run(run):
    root = run
    while root.parent_id:
        root = root.parent
    binding = root.definition.get("ai", {})
    if binding.get("siteEventLaunchId") is not None:
        return SiteEventLaunch.objects.filter(pk=binding["siteEventLaunchId"],
            organization_id=run.organization_id, conversation_id=run.conversation_id).first()
    # A caller-controlled event property cannot manufacture a visitor binding.
    return SiteEventLaunch.objects.filter(organization_id=run.organization_id,
        receipt__deliveries__run_id=root.pk).first()


def current(tenant, claim, *, allow_sent=False):
    from chatballs.webchat.site_events import digest_rule

    organization = lock_organization(tenant.organization_id)
    claim = SiteEventLaunch.objects.select_for_update().get(pk=claim.pk, organization=organization)
    Integration.objects.select_for_update().get(pk=claim.session.connection_id, organization=organization)
    session = WebSession.objects.select_related("widget", "connection__channel__ai_agent", "identity").filter(
        pk=claim.session_id, organization=organization).first()
    if session is None:
        raise ExecutionDenied("site_event_suppressed")
    rule = session.connection.config.get("siteEvent")
    agent = getattr(session.connection.channel, "ai_agent", None)
    if (claim.state not in ({"pending", "running", "sent"} if allow_sent else {"pending", "running"})
            or not available_session(session, claim.origin) or not has_current_consent(session)
            or not rule or not rule["active"] or rule["id"] != claim.rule_id or digest_rule(rule) != claim.rule_digest
            or claim.mode_version != organization.operation_mode_version
            or getattr(agent, "pk", None) != claim.agent_id_snapshot
            or configuration_version(agent) != claim.agent_version
            or not autonomous_allowed(session.connection.channel, organization=organization, connection=session.connection)):
        raise ExecutionDenied("site_event_suppressed")
    conversation = None
    if claim.conversation_id:
        conversation = Conversation.objects.select_for_update(of=("self",)).select_related("channel__ai_agent", "contact", "connection").filter(
            pk=claim.conversation_id, organization=organization, channel_id=session.connection.channel_id,
            connection_id=session.connection_id, contact_id=session.identity.contact_id).first()
        if (conversation is None or conversation.ai_control_version != claim.control_version
                or not autonomous_allowed(conversation.channel, organization=organization,
                    connection=conversation.connection, conversation=conversation)
                or conversation.messages.exclude(pk=claim.response_id).exists()):
            raise ExecutionDenied("site_event_suppressed")
    elif has_history(session):
        raise ExecutionDenied("site_event_suppressed")
    if claim.state != "sent" and expired(claim):
        raise ExecutionDenied("site_event_suppressed")
    return claim, session, conversation


def authorize_run(tenant, run):
    claim = for_run(run)
    if claim is None:
        return None
    if run.cancel_requested_at or run.data_cleared_at:
        raise ExecutionDenied("site_event_suppressed")
    claim, session, conversation = current(tenant, claim, allow_sent=True)
    if run.conversation_id != claim.conversation_id or conversation is None:
        raise ExecutionDenied("context")
    if run.definition["document"]["access"]["scope"] == "organization":
        raise ExecutionDenied("context")
    return claim
