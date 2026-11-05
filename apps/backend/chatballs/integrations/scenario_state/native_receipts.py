"""An encrypted confirmed native outcome, bound to one immutable effect."""

from django.db import models

from chatballs.integrations.scenario_state.documents import EncryptedDocumentModel


class NativeEffectReceipt(EncryptedDocumentModel):
    tenant_relation_fields = ("step",)
    step = models.OneToOneField("integrations.ScenarioStep", on_delete=models.CASCADE,
        related_name="native_receipt")
    invocation_digest = models.CharField(max_length=64)
