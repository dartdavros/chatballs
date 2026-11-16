"""Private file identities, durable upload attempts and authorization grants."""

import uuid

from django.db import models
from django.utils import timezone

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentFile(TenantRelationModel):
    tenant_relation_fields = ("session", "source_message")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session = models.ForeignKey("ai.ExternalAgentSession", on_delete=models.SET_NULL, null=True)
    authorization_id = models.UUIDField()
    upload_id = models.UUIDField(null=True)
    upload_scope = models.CharField(max_length=64, unique=True, null=True)
    attempted_at = models.DateTimeField(default=timezone.now)
    # Incoming bytes stay in their original Message storage, never copied/exported publicly.
    source_message = models.OneToOneField("conversations.Message", on_delete=models.SET_NULL, null=True)
    file = models.FileField(max_length=512, blank=True)
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    complete = models.BooleanField(default=False)
    owned = models.BooleanField(default=True)
    released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["session", "upload_id"], name="external_upload_identity_unique")]


class ExternalAgentFileGrant(TenantRelationModel):
    tenant_relation_fields = ("file", "request")
    file = models.ForeignKey(ExternalAgentFile, on_delete=models.CASCADE, related_name="grants")
    request = models.ForeignKey("ai.ExternalAgentRequest", on_delete=models.CASCADE)
    authorization_id = models.UUIDField()

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["file", "request"], name="external_file_grant_unique")]
