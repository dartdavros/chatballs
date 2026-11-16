"""External outcomes enter the existing employee queue without public summary."""

from chatballs.conversations.domain_events import record_queue_entry
from chatballs.conversations.queue import QUEUE_FIELDS, enter_queue
from chatballs.i18n import t
from chatballs.notifications.models import NotificationAudience, NotificationType
from chatballs.notifications.services import notify


def handoff(conversation, context, *, operation_id, summary="", reason=""):
    from chatballs.ai.diagnostic_redaction import DiagnosticRedactor, integration_secrets
    from chatballs.ai.external_agents.notice_models import ExternalAgentNotice
    from chatballs.ai.pseudonymization import Pseudonymizer
    from chatballs.integrations.models import Integration

    summary = DiagnosticRedactor(Pseudonymizer(), integration_secrets(Integration.objects.filter(
        organization_id=conversation.organization_id))).text(summary[:2000]).replace("[redacted]", "••••")
    kind = {"deadline_exceeded": "timeout", "history_content_unavailable": "voiceFailure"}.get(reason)
    ExternalAgentNotice.objects.get_or_create(conversation=conversation, operation_id=operation_id,
        kind=kind or ("unavailable" if reason else "handoff"), defaults={"summary": summary[:2000]})
    if conversation.is_test:
        from chatballs.ai.external_agents.test_delivery import handoff_test

        return handoff_test(conversation)
    entered = enter_queue(conversation)
    conversation.save(update_fields=QUEUE_FIELDS)
    conversation.refresh_from_db()
    record_queue_entry(conversation, entered=entered, actor_kind="AI")
    notify(
        context=context, type=NotificationType.OPERATOR_REQUESTED,
        audience=NotificationAudience.OPERATORS, audience_group=conversation.group,
        title="", title_key="notifications.operator_needed",
        text_params={"contact": (conversation.contact.name if conversation.contact else "") or t("conversations.guest")}, body=summary,
        target_id=conversation.pk, source_type="Conversation", source_id=conversation.pk,
        dedup_key=f"external-handoff:{operation_id}",
    )
