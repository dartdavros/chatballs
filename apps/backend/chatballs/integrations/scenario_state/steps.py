"""Independent checkpoints ready for full paths, branches and continuations."""

import uuid

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class ScenarioStep(EncryptedDocumentModel):
    tenant_relation_fields = ("run", "integration")
    run = models.ForeignKey("integrations.ScenarioRun", on_delete=models.CASCADE, related_name="steps")
    path = models.CharField(max_length=512)
    integration = models.ForeignKey("integrations.Integration", null=True, on_delete=models.PROTECT)
    adapter_key = models.CharField(max_length=64, blank=True)
    adapter_version = models.PositiveIntegerField()
    operation_key = models.CharField(max_length=100)
    effect_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    retry_strategy = models.CharField(max_length=32)
    state = models.CharField(max_length=24, default="queued")
    attempt = models.PositiveIntegerField(default=0)
    fence = models.PositiveBigIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    sent_at = models.DateTimeField(null=True)
    due_at = models.DateTimeField()
    error_code = models.CharField(max_length=64, blank=True)
    confirmed_digest = models.CharField(max_length=64, blank=True)
    approval_expires_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("run", "path"), name="scenario_step_path")]
        indexes = [models.Index(fields=("organization", "state", "due_at"), name="scenario_steps_due")]
