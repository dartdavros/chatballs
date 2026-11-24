"""Reject deletion when Django would change records outside the demo registry."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.deletion import get_candidate_relations_to_delete

from chatballs.ai.models import KnowledgeFragment
from chatballs.conversations.conversation_models import Conversation, ConversationRead
from chatballs.identity.audit_models import AuditEvent
from chatballs.identity.demo_models import DemoDataset
from chatballs.integrations.models import Integration
from chatballs.notifications.models import Notification, NotificationPreference, NotificationRead

_DEPENDENT_METADATA = {
    ("conversations.conversation_labels", "conversation"),
    ("conversations.conversationread", "conversation"),
    ("notifications.notificationread", "notification"),
    ("webchat.visitorobservation", "session"),
}
_USER_READ_RECEIPTS = {
    ConversationRead: ("conversation_id", Conversation),
    NotificationRead: ("notification_id", Notification),
}


class DemoWorkingReference(ValidationError):
    def __init__(self, model_label, field):
        self.model_label = model_label
        self.field = field
        super().__init__("Demo data is referenced by a working record.", code="working_reference")


def assert_demo_references(instance, owned, dataset):
    for relation in get_candidate_relations_to_delete(instance._meta):
        field = relation.field
        related_model = relation.related_model
        # Search chunks have exactly one source. Its deletion already owns the
        # derived index rows, including chunks bulk-created by older seeds.
        if related_model is KnowledgeFragment and field.name in {"knowledge", "portal_article"}:
            continue
        if (related_model._meta.label_lower, field.name) in _DEPENDENT_METADATA and field.remote_field.on_delete is models.CASCADE:
            # Read receipts and heartbeats belong exclusively to their parent.
            continue
        references = related_model._base_manager.filter(**{field.name: instance})
        if related_model is NotificationPreference and field.name == "user":
            references = references.exclude(organization_id=dataset.organization_id)
        if field.name == "user" and related_model in _USER_READ_RECEIPTS:
            parent_field, parent_model = _USER_READ_RECEIPTS[related_model]
            references = references.exclude(**{f"{parent_field}__in": owned.get(parent_model, ())})
        if related_model is DemoDataset and field.name == "requested_by":
            references = references.exclude(pk=dataset.pk)
        if related_model is AuditEvent and field.name == "actor":
            # These records survive the account via the nullable audit actor FK.
            references = references.exclude(
                organization_id=dataset.organization_id, object_type="DemoDataset", object_id=str(dataset.pk),
                action__in=("demo.reinstall_requested", "demo.reinstall_failed", "demo.reinstalled"),
            ).exclude(
                organization__isnull=True, action__in=("identity.login_succeeded", "identity.logout"),
            ).exclude(
                organization_id=dataset.organization_id, object_type="Organization",
                object_id__in=(str(dataset.organization_id), str(dataset.organization.public_id)),
                action="administration.organization_updated",
            ).exclude(
                organization_id=dataset.organization_id, object_type="Integration",
                object_id__in=owned.get(Integration, ()),
                action__in=("integrations.integration_tested", "integrations.service_renamed", "integrations.integration_updated"),
            ).exclude(
                organization_id=dataset.organization_id, object_type="Conversation",
                object_id__in=owned.get(Conversation, ()),
                action__in=("conversations.claimed", "conversations.assignee_changed"),
            )
        if related_model._meta.auto_created:
            assert_demo_links(references, field, owned)
        elif references.exclude(pk__in=owned.get(related_model, ())).exists():
            raise DemoWorkingReference(related_model._meta.label_lower, field.name)


def assert_demo_links(references, origin, owned):
    for field in references.model._meta.fields:
        if field is origin or not isinstance(field, models.ForeignKey):
            continue
        target = field.remote_field.model
        if references.exclude(**{f"{field.attname}__in": owned.get(target, ())}).exists():
            raise DemoWorkingReference(target._meta.label_lower, field.name)
