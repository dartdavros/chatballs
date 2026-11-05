"""The original reply audit, shared by HTTP and domain application services."""

from chatballs.identity.audit import record_audit_event


def audit_reply(context, action, conversation, *, request=None):
    record_audit_event(action=f"conversations.{action}", actor=context.actor_user,
        organization=context.organization, object_type="Conversation",
        object_id=str(conversation.pk), request=request)
