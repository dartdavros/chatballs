"""Customer-facing queries exclude explicitly isolated agent test conversations."""

from django.apps import apps
from django.db import models


class CustomerConversations(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_test=False)


class CustomerMessages(models.Manager):
    def get_queryset(self):
        return without_suppressed(super().get_queryset().filter(conversation__is_test=False))


def without_suppressed(messages):
    """Apply before pagination, including to explicitly authorized test history."""
    items = apps.get_model("ai", "ExternalAgentDeliveryItem")
    return messages.exclude(ai_delivery__contains={"externalDelivery": {"state": "suppressed"}}).filter(
        ~models.Exists(items.objects.filter(state="suppressed", message_id=models.OuterRef("pk"))))
