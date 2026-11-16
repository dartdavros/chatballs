"""Stable session identity; authority is issued against monotonic persisted versions."""

import uuid

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentSession(TenantRelationModel):
    tenant_relation_fields = ("connection", "agent", "conversation")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    connection = models.ForeignKey("ai.ExternalAgentConnection", on_delete=models.PROTECT)
    agent = models.ForeignKey("ai.AIAgent", on_delete=models.CASCADE)
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE)
    # A changed binding/execution generation starts fresh memory, even in A→B→A.
    binding_version = models.PositiveBigIntegerField()
    execution_version = models.PositiveBigIntegerField()
    external_session_id = models.CharField(max_length=255, blank=True)
    authorization_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    authorization_versions = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["connection", "agent", "conversation", "binding_version", "execution_version"],
            name="external_agent_session_generation",
        )]
