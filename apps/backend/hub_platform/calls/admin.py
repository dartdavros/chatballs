from django.contrib import admin

from hub_platform.calls.models import CallInvite, CallMetric, CallParticipant, CallSession


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "status", "initiated_by", "requested_at", "ended_at"]
    list_filter = ["organization", "status"]
    search_fields = ["id", "conversation__id", "initiated_by__email"]


@admin.register(CallInvite)
class CallInviteAdmin(admin.ModelAdmin):
    list_display = ["id", "call_session", "delivery_status", "expires_at", "opened_at", "responded_at"]
    list_filter = ["delivery_status"]
    exclude = ["token_hash"]


@admin.register(CallParticipant)
class CallParticipantAdmin(admin.ModelAdmin):
    list_display = ["call_session", "side", "last_connection_state", "joined_at", "left_at"]
    list_filter = ["side", "last_connection_state"]


@admin.register(CallMetric)
class CallMetricAdmin(admin.ModelAdmin):
    list_display = ["call_session", "side", "connection_type", "round_trip_ms", "updated_at"]
    list_filter = ["connection_type", "side"]
