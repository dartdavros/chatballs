"""Durable automation state; installing schema never enables execution."""

import uuid

from django.db import models
from django.utils import timezone

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel
from chatballs.tenancy.models import TenantRelationModel


class ScenarioAutomation(TenantRelationModel):
    tenant_relation_fields = ("scenario", "delegate")
    scenario = models.OneToOneField("integrations.ScenarioDefinition", on_delete=models.CASCADE, related_name="automation")
    delegate = models.ForeignKey("identity.OrganizationMembership", null=True, on_delete=models.SET_NULL)
    authorized_at = models.DateTimeField(null=True)


class EventSubscription(TenantRelationModel):
    tenant_relation_fields = ("scenario", "integration")
    scenario = models.ForeignKey("integrations.ScenarioDefinition", on_delete=models.CASCADE, related_name="event_subscriptions")
    integration = models.ForeignKey("integrations.Integration", null=True, on_delete=models.CASCADE)
    trigger_id = models.CharField(max_length=100)
    event_key = models.CharField(max_length=100)
    active = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("scenario", "trigger_id"), name="scenario_event_subscription")]
        indexes = [models.Index(fields=("organization", "integration", "event_key", "active"), name="scenario_event_subscribers")]


class EventDelivery(TenantRelationModel):
    tenant_relation_fields = ("receipt", "scenario", "run")
    receipt = models.ForeignKey("integrations.EventReceipt", on_delete=models.CASCADE, related_name="deliveries")
    scenario = models.ForeignKey("integrations.ScenarioDefinition", null=True, on_delete=models.SET_NULL)
    scenario_key = models.CharField(max_length=36)
    trigger_id = models.CharField(max_length=100)
    run = models.ForeignKey("integrations.ScenarioRun", null=True, on_delete=models.SET_NULL)
    state = models.CharField(max_length=16, default="pending")
    error_code = models.CharField(max_length=64, blank=True)
    due_at = models.DateTimeField(default=timezone.now)
    lease_until = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("receipt", "scenario_key"), name="event_delivery_subscriber")]


class ScheduleCheckpoint(TenantRelationModel):
    tenant_relation_fields = ("scenario",)
    scenario = models.ForeignKey("integrations.ScenarioDefinition", on_delete=models.CASCADE, related_name="schedules")
    trigger_id = models.CharField(max_length=100)
    configuration_hash = models.CharField(max_length=64)
    checked_at = models.DateTimeField()
    due_at = models.DateTimeField()
    last_slot = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("scenario", "trigger_id"), name="scenario_schedule_trigger")]


class PollCursor(EncryptedDocumentModel):
    tenant_relation_fields = ("integration",)
    integration = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="event_cursors")
    event_key = models.CharField(max_length=100)
    due_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True)
    fence = models.UUIDField(default=uuid.uuid4)
    failures = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("integration", "event_key"), name="service_event_poll_cursor")]
