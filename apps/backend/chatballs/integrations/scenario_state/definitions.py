"""Tenant-owned editable definitions; no publication lifecycle or execution."""

import uuid

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel
from chatballs.tenancy.models import TenantRelationModel


class ScenarioDefinition(EncryptedDocumentModel):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=200)
    category_path = models.JSONField(default=list, blank=True)
    revision = models.PositiveIntegerField(default=1)
    enabled = models.BooleanField(default=False)
    # Parameters may contain sensitive constants. Plain audit/outbox must never
    # copy this document. Runtime will take its own encrypted execution snapshot.
    origin_adapter = models.CharField(max_length=64, blank=True)
    origin_key = models.CharField(max_length=100, blank=True)
    origin_version = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ScenarioConnection(TenantRelationModel):
    tenant_relation_fields = ("scenario", "integration")
    scenario = models.ForeignKey(ScenarioDefinition, on_delete=models.CASCADE, related_name="connections")
    integration = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="scenarios")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("scenario", "integration"), name="scenario_connection_unique")]
