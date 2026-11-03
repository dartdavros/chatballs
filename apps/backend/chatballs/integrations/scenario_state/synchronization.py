"""Saved exchange configuration. Entity links and effects belong to T-172."""

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class ServiceSynchronizationSettings(EncryptedDocumentModel):
    tenant_relation_fields = ("integration", "delegate")
    integration = models.OneToOneField("integrations.Integration", on_delete=models.CASCADE, related_name="synchronization_settings")
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delegate = models.ForeignKey("identity.OrganizationMembership", null=True, on_delete=models.SET_NULL)


class SynchronizationCheckpoint(EncryptedDocumentModel):
    tenant_relation_fields = ("settings", "link", "run")
    settings = models.ForeignKey(ServiceSynchronizationSettings, on_delete=models.CASCADE, related_name="checkpoints")
    link = models.ForeignKey("integrations.EntityLink", on_delete=models.CASCADE, related_name="checkpoints")
    pair_id = models.CharField(max_length=100)
    generation = models.PositiveBigIntegerField(default=0)
    state = models.CharField(max_length=24, default="idle")
    due_at = models.DateTimeField()
    run = models.ForeignKey("integrations.ScenarioRun", null=True, on_delete=models.SET_NULL)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("settings", "link", "pair_id"), name="synchronization_link_pair")]
