"""Employee-facing facts kept separate from encrypted recovery records."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentNotice(TenantRelationModel):
    tenant_relation_fields = ("conversation",)
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE)
    operation_id = models.UUIDField()
    kind = models.CharField(max_length=16)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "operation_id", "kind"],
                                               name="external_notice_once")]
