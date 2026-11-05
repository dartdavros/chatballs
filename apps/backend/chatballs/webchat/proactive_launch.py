"""Bind the shared fan-out to one visitor before its immutable Run is captured."""

from chatballs.conversations.models import ControlMode, Conversation, ExpectedResponder
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.webchat.proactive_guards import current
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.site_event_config import configured_scenario


def prepare(tenant, receipt, scenario):
    claim = SiteEventLaunch.objects.filter(organization_id=tenant.organization_id, receipt=receipt).first()
    if claim is None:
        raise ExecutionDenied("permission")
    claim, session, conversation = current(tenant, claim)
    configured = configured_scenario(session.connection)
    if configured.pk != scenario.pk or scenario.definition["access"]["scope"] == "organization":
        raise ExecutionDenied("context")
    if conversation is None:
        conversation = Conversation.objects.create(organization_id=tenant.organization_id,
            channel=session.connection.channel, group=session.connection.channel.group,
            connection=session.connection, contact=session.identity.contact,
            control_mode=ControlMode.AI, expected_responder=ExpectedResponder.AI,
            transport_meta={"webChatWidgetId": session.widget_id, "siteEventLaunchId": claim.pk})
        claim.conversation = conversation
        claim.control_version = conversation.ai_control_version
        claim.save(update_fields=["conversation", "control_version"])
    return conversation.pk
