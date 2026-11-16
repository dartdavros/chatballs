"""Private product test scope; never a customer, integration or demo fixture."""

import uuid

from django.conf import settings
from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class ExternalAgentTestSession(TenantRelationModel):
    tenant_relation_fields = ("conversation", "agent")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    conversation = models.OneToOneField("conversations.Conversation", on_delete=models.CASCADE,
                                       related_name="external_test_scope")
    agent = models.ForeignKey("ai.AIAgent", on_delete=models.PROTECT)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    context_ciphertext = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
