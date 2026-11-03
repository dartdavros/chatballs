"""A generation can be completed once by a receipt, decision or deadline."""

import uuid

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class ScenarioWait(EncryptedDocumentModel):
    tenant_relation_fields = ("run", "integration", "receipt")
    run = models.ForeignKey("integrations.ScenarioRun", on_delete=models.CASCADE, related_name="waits")
    path = models.CharField(max_length=512)
    generation = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=24)
    integration = models.ForeignKey("integrations.Integration", null=True, on_delete=models.PROTECT)
    event_key = models.CharField(max_length=100, blank=True)
    correlation_hash = models.CharField(max_length=64, blank=True)
    deadline = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=24, default="pending")
    receipt = models.ForeignKey("integrations.EventReceipt", null=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("run", "path"), name="scenario_wait_path")]
        indexes = [models.Index(fields=("organization", "integration", "correlation_hash"), name="scenario_wait_match")]
