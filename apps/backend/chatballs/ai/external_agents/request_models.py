"""Durable FIFO checkpoints; encrypted payloads are separate from diagnostics."""

import uuid

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentRequest(TenantRelationModel):
    tenant_relation_fields = ("session", "conversation", "trigger")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session = models.ForeignKey("ai.ExternalAgentSession", on_delete=models.CASCADE)
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE)
    trigger = models.OneToOneField("conversations.Message", on_delete=models.CASCADE, null=True)
    authorization_id = models.UUIDField()
    authorization_versions = models.JSONField(default=dict)
    sequence = models.PositiveBigIntegerField()
    deadline_at = models.DateTimeField()
    state = models.CharField(max_length=16, default="queued")
    active = models.BooleanField(default=False)
    seed_ciphertext = models.TextField(blank=True)
    snapshot_ciphertext = models.TextField(blank=True)
    history_ciphertext = models.TextField(blank=True)
    snapshot_digest = models.CharField(max_length=64, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    polls = models.PositiveIntegerField(default=0)
    fence = models.PositiveBigIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    next_at = models.DateTimeField()
    terminal_at = models.DateTimeField(null=True)
    cancel_pending = models.BooleanField(default=False)
    reason_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["conversation"], condition=models.Q(active=True),
            name="external_one_active_request",
        )]
        indexes = [models.Index(fields=["conversation", "sequence"], name="external_request_fifo")]
