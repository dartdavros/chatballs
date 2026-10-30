"""Saved exchange configuration. Entity links and effects belong to T-172."""

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class ServiceSynchronizationSettings(EncryptedDocumentModel):
    tenant_relation_fields = ("integration",)
    integration = models.OneToOneField("integrations.Integration", on_delete=models.CASCADE, related_name="synchronization_settings")
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
