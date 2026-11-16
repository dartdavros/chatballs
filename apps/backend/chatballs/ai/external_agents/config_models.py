"""Explicit external connections and per-agent export policy; no implicit grants."""

from django.db import models

from chatballs.identity.crypto import EncryptedCharField
from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentConnection(TenantRelationModel):
    tenant_relation_fields = ("integration",)
    integration = models.OneToOneField("integrations.Integration", on_delete=models.PROTECT,
                                      related_name="external_execution")
    enabled = models.BooleanField(default=True)
    revision = models.PositiveBigIntegerField(default=1)
    credential_version = models.PositiveBigIntegerField(default=1)
    inbound_key_hash = models.CharField(max_length=64, unique=True, null=True, editable=False)
    # Independent from either Bearer credential, retained across revocation and rotation.
    deduplication_key = EncryptedCharField(max_length=128, editable=False)
    capabilities = models.JSONField(default=dict)
    checked_at = models.DateTimeField(null=True)


class ExternalAgentBinding(TenantRelationModel):
    tenant_relation_fields = ("connection", "agent")
    connection = models.ForeignKey(ExternalAgentConnection, on_delete=models.PROTECT,
                                  related_name="bindings")
    agent = models.OneToOneField("ai.AIAgent", on_delete=models.CASCADE,
                                related_name="external_binding")
    external_agent_id = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    revision = models.PositiveBigIntegerField(default=1)
    policy_version = models.PositiveBigIntegerField(default=1)
    policy_accepted = models.BooleanField(default=False)
    standard_fields = models.JSONField(default=list)
    custom_fields = models.JSONField(default=list)
    template_ids = models.JSONField(default=list)
    accepted_definitions = models.JSONField(default=dict)
    proactive_enabled = models.BooleanField(default=False)
    processing_mode = models.CharField(max_length=8, default="ordinary", choices=[("ordinary", "ordinary"), ("long", "long")])
    ordinary_timeout = models.PositiveIntegerField(default=120)
    long_timeout = models.PositiveIntegerField(default=86400)
    maximum_timeout = models.PositiveIntegerField(default=86400)
