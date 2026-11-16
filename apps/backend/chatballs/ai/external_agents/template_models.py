"""Template ID generations survive edits, deletion and recreation."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentTemplateVersion(TenantRelationModel):
    template_id = models.CharField(max_length=255)
    revision = models.PositiveBigIntegerField(default=1)
    definition = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "template_id"],
                                               name="external_template_version_unique")]
