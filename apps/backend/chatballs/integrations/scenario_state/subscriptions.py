"""External launch authentication configured by the editor; delivery is T-172."""

import uuid

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ScenarioExternalKey(TenantRelationModel):
    tenant_relation_fields = ("scenario",)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    scenario = models.ForeignKey("integrations.ScenarioDefinition", on_delete=models.CASCADE, related_name="external_keys")
    trigger_id = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("scenario", "trigger_id"), name="scenario_external_trigger_unique")]
