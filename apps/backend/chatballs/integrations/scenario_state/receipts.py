"""Verified delivery identity survives operational payload cleanup."""

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class EventReceipt(EncryptedDocumentModel):
    tenant_relation_fields = ("integration",)
    integration = models.ForeignKey("integrations.Integration", null=True, on_delete=models.PROTECT)
    source_key = models.CharField(max_length=100)
    event_id_hash = models.CharField(max_length=64)
    event_key = models.CharField(max_length=100)
    correlation_hash = models.CharField(max_length=64, blank=True)
    digest = models.CharField(max_length=64)
    sequence = models.PositiveBigIntegerField(null=True)
    received_at = models.DateTimeField(auto_now_add=True)
    occurred_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    cleared_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("organization", "source_key", "event_id_hash"), name="scenario_receipt_identity")]
        indexes = [models.Index(fields=("organization", "integration", "correlation_hash"), name="scenario_receipt_match")]
