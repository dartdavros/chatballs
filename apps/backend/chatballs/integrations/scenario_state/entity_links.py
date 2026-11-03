"""Explicit tenant-owned identities; email and phone are never identity keys."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class EntityLink(TenantRelationModel):
    tenant_relation_fields = ("integration",)
    integration = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="entity_links")
    internal_kind = models.CharField(max_length=32)
    internal_id = models.PositiveBigIntegerField()
    external_kind = models.CharField(max_length=100)
    external_id = models.CharField(max_length=512)
    revision = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("integration", "internal_kind", "internal_id", "external_kind"), name="entity_link_internal_identity")]
        indexes = [models.Index(fields=("organization", "integration", "external_kind", "external_id"), name="entity_link_external_identity")]


class IntegrationEntityVersion(TenantRelationModel):
    internal_kind = models.CharField(max_length=32)
    internal_id = models.PositiveBigIntegerField()
    version = models.PositiveBigIntegerField(default=1)
    modified_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("organization", "internal_kind", "internal_id"), name="integration_entity_version")]
