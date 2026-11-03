"""Encrypted interpreter frames, separate from the immutable run snapshot."""

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel
from chatballs.tenancy.models import TenantRelationModel


class ScenarioProgress(EncryptedDocumentModel):
    tenant_relation_fields = ("run",)
    run = models.ForeignKey("integrations.ScenarioRun", on_delete=models.CASCADE, related_name="progress")
    path = models.CharField(max_length=512)
    parent_path = models.CharField(max_length=512, blank=True)
    kind = models.CharField(max_length=16)
    state = models.CharField(max_length=24, default="queued")
    error_code = models.CharField(max_length=64, blank=True)
    payload_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("run", "path"), name="scenario_progress_path")]


class ScenarioBudget(TenantRelationModel):
    tenant_relation_fields = ("root",)
    root = models.OneToOneField("integrations.ScenarioRun", on_delete=models.CASCADE, related_name="budget")
    instances = models.PositiveIntegerField(default=0)
    active_seconds = models.FloatField(default=0)
    payload_bytes = models.PositiveBigIntegerField(default=0)
