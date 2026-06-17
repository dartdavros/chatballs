import uuid

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InboxEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source", models.CharField(max_length=128)),
                ("external_event_id", models.CharField(max_length=256)),
                ("payload_hash", models.CharField(max_length=128)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="OutboxEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("aggregate_type", models.CharField(max_length=128)),
                ("aggregate_id", models.CharField(max_length=128)),
                ("event_type", models.CharField(max_length=128)),
                ("payload", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("PROCESSED", "Processed"),
                            ("FAILED", "Failed"),
                            ("DEAD_LETTER", "Dead letter"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=32,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("next_attempt_at", models.DateTimeField(db_index=True, default=timezone.now)),
                ("correlation_id", models.CharField(blank=True, max_length=128)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="inboxevent",
            constraint=models.UniqueConstraint(
                fields=("source", "external_event_id"),
                name="uniq_inbox_source_external_event_id",
            ),
        ),
        migrations.AddIndex(
            model_name="outboxevent",
            index=models.Index(fields=["status", "next_attempt_at"], name="events_outb_status_881ef5_idx"),
        ),
        migrations.AddIndex(
            model_name="outboxevent",
            index=models.Index(fields=["aggregate_type", "aggregate_id"], name="events_outb_aggrega_a2b510_idx"),
        ),
    ]
