from django.contrib import admin

from chatballs.events.models import InboxEvent, OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ["id", "event_type", "aggregate_type", "aggregate_id", "status", "attempts", "created_at", "processed_at"]
    list_filter = ["status", "event_type", "aggregate_type"]
    search_fields = ["id", "aggregate_id", "event_type", "correlation_id"]
    readonly_fields = [
        "id",
        "aggregate_type",
        "aggregate_id",
        "event_type",
        "payload",
        "status",
        "attempts",
        "next_attempt_at",
        "correlation_id",
        "last_error",
        "created_at",
        "processed_at",
    ]


@admin.register(InboxEvent)
class InboxEventAdmin(admin.ModelAdmin):
    list_display = ["source", "external_event_id", "received_at", "processed_at"]
    list_filter = ["source"]
    search_fields = ["source", "external_event_id", "payload_hash"]
    readonly_fields = ["id", "source", "external_event_id", "payload_hash", "received_at", "processed_at"]
