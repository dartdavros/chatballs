"""Content-free accepted operation identities survive delivery checkpoint retention."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentOperation(TenantRelationModel):
    tenant_relation_fields = ("session",)
    session = models.ForeignKey("ai.ExternalAgentSession", on_delete=models.CASCADE)
    operation = models.CharField(max_length=16)
    public_id = models.UUIDField()
    authorization_id = models.UUIDField()
    digest = models.CharField(max_length=64)
    ack = models.JSONField(default=dict)
    # Exact post-handoff versions: only this operation's revocation is exempted.
    post_versions = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["session", "operation", "public_id"], name="external_operation_identity",
        )]
