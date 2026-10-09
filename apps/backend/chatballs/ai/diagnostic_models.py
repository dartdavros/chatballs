from django.db import models

from chatballs.tenancy.models import TenantRelationModel


class TurnDiagnostic(TenantRelationModel):
    """Redacted trace tied to the incoming message; deleted with its conversation."""

    tenant_relation_fields = ("message",)
    message = models.OneToOneField(
        "conversations.Message", on_delete=models.CASCADE, related_name="ai_diagnostic"
    )
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"turn-diagnostic:{self.message_id}"
