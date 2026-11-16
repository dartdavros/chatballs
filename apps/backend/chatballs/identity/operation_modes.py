"""Organization-wide autonomous conversation policy and serialized transitions."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction

from chatballs.i18n import t


class OperationMode(models.TextChoices):
    AI_AGENTS = "AI_AGENTS", "AI agents"
    OPERATORS_ONLY = "OPERATORS_ONLY", "Operators only"


def lock_organization(organization_id):
    # Always take this lock before a conversation lock, including delivery.
    from chatballs.identity.models import Organization

    return Organization.objects.select_for_update(no_key=True).get(pk=organization_id)


def autonomous_allowed(channel, *, organization, connection=None, conversation=None):
    agent = getattr(channel, "ai_agent", None)
    provider = getattr(agent, "provider_integration", None) or channel.provider_integration
    if agent and agent.execution_mode == "external":
        from chatballs.ai.external_agents.readiness import consent_current, ready

        return bool(
            organization.operation_mode == OperationMode.AI_AGENTS
            and channel.organization_id == organization.pk and channel.is_active and agent.is_active
            and ready(agent, organization)
            and (connection is None or (connection.is_active and connection.channel_id == channel.pk
                                       and connection.organization_id == organization.pk))
            and (conversation is None or (conversation.lifecycle == "OPEN" and conversation.archived_at is None and conversation.control_mode == "AI"
                                         and conversation.assigned_operator_id is None and consent_current(conversation)))
        )
    return bool(
        organization.operation_mode == OperationMode.AI_AGENTS
        and channel.organization_id == organization.pk
        and channel.is_active
        and agent and agent.is_active and provider and provider.secret and provider.is_active
        and provider.organization_id == organization.pk
        and (agent.model or provider.config.get("default_model") or provider.provider == "DEMO")
        and (connection is None or (
            connection.is_active and connection.channel_id == channel.pk
            and connection.organization_id == organization.pk
        ))
        and (conversation is None or (
            conversation.lifecycle == "OPEN" and conversation.control_mode == "AI"
            and conversation.assigned_operator_id is None
        ))
    )


def change_operation_mode(*, context, organization, mode):
    """Caller holds the organization lock, audit and queue writes commit together."""
    from chatballs.identity.audit import record_audit_event
    from chatballs.identity.policy import ResourceScope, authorize

    if not authorize(context.membership, "settings.manage", ResourceScope(organization.pk)):
        raise PermissionDenied
    if mode not in OperationMode.values:
        raise ValidationError({"operationMode": t("admin.operation_mode_invalid")})
    previous = organization.operation_mode
    if previous == mode:
        return
    organization.operation_mode = mode
    organization.operation_mode_version += 1
    organization.save(update_fields=["operation_mode", "operation_mode_version"])
    if mode == OperationMode.OPERATORS_ONLY:
        _queue_autonomous_conversations(context, organization)
    record_audit_event(
        action="administration.organization_updated", organization=organization,
        actor=context.actor_user, object_type="Organization", object_id=str(organization.public_id),
        payload={"operationMode": {"previous": previous, "current": mode},
                 "operationModeVersion": organization.operation_mode_version},
    )
    from chatballs.conversations.realtime import inbox_group, notify_inbox_changed
    from chatballs.realtime import publish

    transaction.on_commit(lambda: publish(inbox_group(organization.pk), {"type": "organization.changed"}))
    transaction.on_commit(lambda: notify_inbox_changed(organization.pk))


def _queue_autonomous_conversations(context, organization):
    from chatballs.conversations.domain_events import operation_key, record_queue_entry
    from chatballs.conversations.models import AiTurnState, Conversation, Message
    from chatballs.conversations.queue import QUEUE_FIELDS, enter_queue
    from chatballs.notifications.models import NotificationAudience, NotificationType
    from chatballs.notifications.services import notify

    conversations = Conversation.objects.select_for_update().filter(
        organization=organization, lifecycle="OPEN", control_mode="AI",
        assigned_operator__isnull=True,
    )
    for conversation in conversations:
        entered = enter_queue(conversation)
        conversation.save(update_fields=QUEUE_FIELDS)
        operation_id = operation_key("operation-mode", f"{organization.operation_mode_version}:{conversation.pk}")
        record_queue_entry(conversation, entered=entered, operation_id=operation_id)
        if entered:
            notify(
                context=context, type=NotificationType.OPERATOR_REQUESTED,
                audience=NotificationAudience.OPERATORS, audience_group=conversation.group,
                title_key="notifications.operator_needed", title="", body="",
                text_params={"contact": (conversation.contact.name if conversation.contact else "") or t("conversations.guest")},
                target_id=conversation.pk, source_type="Conversation", source_id=conversation.pk,
                dedup_key=f"operation-mode:{operation_id}",
            )
    Message.objects.filter(
        organization=organization, ai_turn_state__in=[AiTurnState.PENDING, AiTurnState.RUNNING],
    ).update(ai_turn_state=AiTurnState.DONE)


def serialize_autonomy(function):
    from functools import wraps

    from chatballs.tenancy.database import tenant_atomic

    @wraps(function)
    def execute(*, context, **kwargs):
        with tenant_atomic(context):
            lock_organization(context.organization_id)
            return function(context=context, **kwargs)
    return execute
