"""Native change clocks are recorded with domain writes, never guessed on read."""

from django.db.models import F
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from chatballs.conversations.models import Contact, Conversation
from chatballs.integrations.scenario_state.entity_links import IntegrationEntityVersion


def record(instance, deleted):
    kind = "contact" if isinstance(instance, Contact) else "conversation"
    key = {"organization_id": instance.organization_id, "internal_kind": kind, "internal_id": instance.pk}
    # Caller/domain transaction owns the row change and this clock together.
    row, created = IntegrationEntityVersion.objects.get_or_create(**key,
        defaults={"modified_at": timezone.now(), "deleted": deleted})
    if not created:
        IntegrationEntityVersion.objects.filter(pk=row.pk).update(version=F("version") + 1,
            modified_at=timezone.now(), deleted=deleted)


@receiver(post_save, sender=Contact, dispatch_uid="integration-contact-version")
@receiver(post_save, sender=Conversation, dispatch_uid="integration-conversation-version")
def changed(sender, instance, raw=False, **kwargs):
    if not raw:
        record(instance, False)


@receiver(pre_delete, sender=Contact, dispatch_uid="integration-contact-deletion")
@receiver(pre_delete, sender=Conversation, dispatch_uid="integration-conversation-deletion")
def deleted(sender, instance, **kwargs):
    record(instance, True)
