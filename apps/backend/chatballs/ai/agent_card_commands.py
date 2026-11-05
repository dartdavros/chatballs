"""Audited agent commands used by both product entry points."""

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.ai import agent_card as cards
from chatballs.ai.agent_card_queries import require
from chatballs.channels import services as channels
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event


def _audit(context, action, channel, *, request=None, identifier=None, **payload):
    record_audit_event(action=action, actor=context.actor_user, organization=context.organization,
        object_type="Agent", object_id=str(identifier if identifier is not None else channel.id),
        payload=payload or None, request=request)


@transaction.atomic
def create(context, body, *, request=None):
    require(context, "ai.manage")
    group_id = body.get("groupId")
    if group_id is not None and (isinstance(group_id, bool) or not isinstance(group_id, int)):
        raise ValidationError(t("ai.group_id_integer_or_null"))
    channel = cards.create_agent_card(context=context, name=body.get("name"), group_id=group_id)
    _audit(context, "ai.agent_created", channel, name=channel.name, request=request)
    channel = cards.agent_card_for_context(context=context, agent_id=channel.id)
    return {"agent": cards.agent_card_payload(channel)}


@transaction.atomic
def update(context, agent_id, body, *, request=None):
    require(context, "ai.manage")
    channel = cards.agent_card_for_context(context=context, agent_id=agent_id)
    channel = cards.update_agent_card(context=context, channel=channel, body=body)
    _audit(context, "ai.agent_updated", channel, fields=sorted(body), request=request)
    return {"agent": cards.agent_card_payload(channel, check_tool_support=True)}


@transaction.atomic
def delete(context, agent_id, *, request=None):
    require(context, "ai.manage")
    channel = cards.agent_card_for_context(context=context, agent_id=agent_id)
    name = channel.name
    cards.delete_agent_card(context=context, channel=channel)
    _audit(context, "ai.agent_deleted", channel, identifier=agent_id, name=name, request=request)
    return {}


def set_active(context, agent_id, active):
    require(context, "ai.manage")
    channel = cards.agent_card_for_context(context=context, agent_id=agent_id)
    channel = cards.set_agent_card_active(context=context, channel=channel, is_active=active)
    return {"agent": cards.agent_card_payload(channel)}


@transaction.atomic
def bind(context, agent_id, body, *, request=None):
    require(context, "integrations.manage")
    channel = cards.agent_card_for_context(context=context, agent_id=agent_id)
    integration_id = body.get("integrationId")
    if isinstance(integration_id, bool) or not isinstance(integration_id, int):
        raise ValidationError(t("ai.integration_id_integer"))
    integration, previous = channels.bind_connection(context=context, channel=channel,
        integration_id=integration_id, force=bool(body.get("force")))
    _audit(context, "channels.connection_moved" if previous is not None else "channels.connection_bound",
        channel, integrationId=integration.id, request=request,
        **({"fromChannelId": previous} if previous is not None else {}))
    channel = cards.agent_card_for_context(context=context, agent_id=channel.id)
    return {"agent": cards.agent_card_payload(channel)}


@transaction.atomic
def unbind(context, agent_id, integration_id, *, request=None):
    require(context, "integrations.manage")
    channel = cards.agent_card_for_context(context=context, agent_id=agent_id)
    channels.unbind_connection(context=context, channel=channel, integration_id=integration_id)
    _audit(context, "channels.connection_unbound", channel, integrationId=integration_id, request=request)
    channel = cards.agent_card_for_context(context=context, agent_id=channel.id)
    return {"agent": cards.agent_card_payload(channel)}
