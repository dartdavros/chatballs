"""Once-rule identity; payload stays in the shared encrypted receipt/Run stores."""

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class SiteEventLaunch(TenantRelationModel):
    tenant_relation_fields = ("session", "receipt", "conversation", "response")
    session = models.ForeignKey("webchat.WebSession", on_delete=models.CASCADE, related_name="site_event_launches")
    rule_id = models.CharField(max_length=32)
    rule_digest = models.CharField(max_length=64)
    origin = models.CharField(max_length=2048)
    receipt = models.OneToOneField("integrations.EventReceipt", null=True, on_delete=models.SET_NULL)
    conversation = models.ForeignKey("conversations.Conversation", null=True, on_delete=models.SET_NULL)
    response = models.OneToOneField("conversations.Message", null=True, on_delete=models.SET_NULL)
    mode_version = models.PositiveBigIntegerField()
    control_version = models.PositiveBigIntegerField(default=0)
    agent_id_snapshot = models.PositiveBigIntegerField()
    agent_version = models.CharField(max_length=64)
    state = models.CharField(max_length=16, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("session", "rule_id"), name="site_event_once_session_rule")]
