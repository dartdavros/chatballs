"""Durable execution identity. Revision is deliberately absent from dedup."""

import uuid

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class ScenarioRun(EncryptedDocumentModel):
    tenant_relation_fields = ("scenario", "initiator", "conversation")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    scenario = models.ForeignKey("integrations.ScenarioDefinition", null=True, on_delete=models.SET_NULL)
    scenario_key = models.CharField(max_length=160)
    trigger_key = models.CharField(max_length=64)
    revision = models.PositiveIntegerField()
    initiator = models.ForeignKey("identity.OrganizationMembership", null=True, on_delete=models.SET_NULL)
    conversation = models.ForeignKey("conversations.Conversation", null=True, on_delete=models.SET_NULL)
    state = models.CharField(max_length=24, default="queued")
    cancel_requested_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)
    data_cleared_at = models.DateTimeField(null=True)
    journal_cleared_at = models.DateTimeField(null=True)
    structure = models.JSONField(default=dict)
    # Minimal tombstone survives cleanup: manual request keys have no expiry.

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("organization", "scenario_key", "trigger_key"), name="scenario_run_dedup",
        )]
        indexes = [models.Index(fields=("organization", "-created_at"), name="scenario_runs_recent")]
