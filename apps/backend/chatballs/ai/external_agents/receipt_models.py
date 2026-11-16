"""Immutable terminal receipts and content-free connection-lifetime deduplication."""

import uuid

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentReceipt(TenantRelationModel):
    tenant_relation_fields = ("request",)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    request = models.OneToOneField("ai.ExternalAgentRequest", on_delete=models.CASCADE)
    result_id = models.UUIDField()
    digest = models.CharField(max_length=64)
    payload_ciphertext = models.TextField(blank=True)
    ack = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class ExternalAgentTombstone(TenantRelationModel):
    tenant_relation_fields = ("connection",)
    connection = models.ForeignKey("ai.ExternalAgentConnection", on_delete=models.CASCADE)
    request_id = models.UUIDField(unique=True)
    trigger_digest = models.CharField(max_length=64)
    result_id = models.UUIDField(null=True)
    digest = models.CharField(max_length=64, blank=True)
    ack = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["connection", "result_id"], name="external_result_id_unique",
        )]
