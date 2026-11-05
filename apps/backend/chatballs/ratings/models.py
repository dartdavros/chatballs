"""A completion request owns one immutable customer response."""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class RatingSettings(models.Model):
    organization = models.OneToOneField("identity.Organization", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)
    scale = models.JSONField(default=list, blank=True)
    text = models.TextField(default="", blank=True)
    delay_seconds = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"rating-settings:{self.organization_id}"


class RatingRequest(TenantRelationModel):
    tenant_relation_fields = ("conversation", "completion")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE)
    completion = models.OneToOneField("conversations.ConversationEvent", on_delete=models.CASCADE)
    scale = models.JSONField()
    text = models.TextField()
    delay_seconds = models.PositiveIntegerField()
    responder_ids = models.JSONField(default=list)
    delivery_session_id = models.PositiveBigIntegerField(null=True, blank=True)
    due_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    credential_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "due_at"], name="rating_due_idx")]
        constraints = [
            models.UniqueConstraint(fields=["conversation", "completion"], name="rating_completion_unique"),
            models.CheckConstraint(
                condition=models.Q(sent_at__isnull=True, credential_hash__isnull=True, expires_at__isnull=True)
                | models.Q(sent_at__isnull=False, credential_hash__isnull=False),
                name="rating_credential_lifecycle",
            ),
        ]

    def validate_tenant_relations(self):
        super().validate_tenant_relations()
        if (self.completion.conversation_id != self.conversation_id
                or self.completion.event_type != "CLOSED"):
            raise ValidationError("Rating requires its conversation's completion")

    def __str__(self):
        return f"rating-request:{self.public_id}"


class CustomerRating(TenantRelationModel):
    tenant_relation_fields = ("request",)
    request = models.OneToOneField(RatingRequest, on_delete=models.CASCADE, related_name="result")
    value = models.CharField(max_length=64)
    comment = models.CharField(max_length=2000, blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"customer-rating:{self.request_id}"
