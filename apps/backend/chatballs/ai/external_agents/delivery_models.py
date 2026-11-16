"""One delivery per accepted reply, one message per stable ordered item."""

import uuid

from django.apps import apps
from django.db import models, transaction

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentDelivery(TenantRelationModel):
    tenant_relation_fields = ("request",)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request = models.OneToOneField("ai.ExternalAgentRequest", on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)


class ExternalAgentDeliveryItem(TenantRelationModel):
    tenant_relation_fields = ("delivery", "message")
    delivery = models.ForeignKey(ExternalAgentDelivery, on_delete=models.CASCADE, related_name="items")
    public_id = models.UUIDField()
    position = models.PositiveIntegerField()
    message = models.OneToOneField("conversations.Message", on_delete=models.CASCADE)
    state = models.CharField(max_length=24, default="queued")
    reason_code = models.CharField(max_length=64, blank=True)
    # Set durably before calling a non-idempotent channel. Restart means unknown.
    sending = models.BooleanField(default=False)

    def retain_message_state(self):
        """Message lifetime exceeds the operational request/receipt lifetime."""
        request = self.delivery.request
        fact = {"state": self.state, "initiative": request.trigger_id is None,
                "sequence": request.sequence, "position": self.position}
        message = apps.get_model("conversations", "Message")
        # Merge only our key, preserving file IDs and other private delivery facts.
        message.including_tests.using(self._state.db).filter(pk=self.message_id).update(
            ai_delivery=models.Func(models.F("ai_delivery"), models.Value("{externalDelivery}"),
                models.Value(fact, output_field=models.JSONField()), function="jsonb_set"))

    def save(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get("using") or self._state.db):
            super().save(*args, **kwargs)
            self.retain_message_state()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["delivery", "public_id"], name="external_item_id_unique"),
            models.UniqueConstraint(fields=["delivery", "position"], name="external_item_order_unique"),
        ]
