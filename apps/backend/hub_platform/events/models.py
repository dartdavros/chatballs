import uuid

from django.db import models
from django.utils import timezone


class OutboxStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"
    DEAD_LETTER = "DEAD_LETTER", "Dead letter"


class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    aggregate_type = models.CharField(max_length=128)
    aggregate_id = models.CharField(max_length=128)
    event_type = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=32,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING,
        db_index=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.id}"


class InboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=128)
    external_event_id = models.CharField(max_length=256)
    payload_hash = models.CharField(max_length=128)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_event_id"],
                name="uniq_inbox_source_external_event_id",
            )
        ]

    def __str__(self) -> str:
        return f"{self.source}:{self.external_event_id}"
