from django.db import models

# Один основной sales-агент на продукт (ADR-HUB-0007).
DEFAULT_AI_MODEL = "openai/gpt-4o-mini"


class AIAgent(models.Model):
    product = models.OneToOneField("products.Product", on_delete=models.PROTECT, related_name="ai_agent")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    model = models.CharField(max_length=128, default=DEFAULT_AI_MODEL)
    model_params = models.JSONField(default=dict, blank=True)
    allowed_tools = models.JSONField(default=list, blank=True)
    limits = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.product.code}:agent"
