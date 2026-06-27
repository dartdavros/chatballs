from django.db import models

# Канал обработки — якорь AI-контекста (ADR-HUB-0019). Опциональный продукт,
# отдел перехвата, ссылка на провайдер-интеграцию и модель. Подключения
# (боты/виджеты) и release канала прикручиваются на следующих шагах M1.

# Основная модель компании (ADR: Sonnet 4.6 на OpenRouter).
DEFAULT_CHANNEL_MODEL = "anthropic/claude-sonnet-4.6"


class Channel(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="channels")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    # Отдел, чьи операторы перехватывают диалоги канала.
    department = models.ForeignKey("identity.Department", on_delete=models.PROTECT, related_name="channels", null=True, blank=True)
    # Продукт опционален: непродуктовый канал — главный сайт edevs.
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="channels", null=True, blank=True)
    # LLM-провайдер канала (ADR-HUB-0020) и выбранная модель.
    provider_integration = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="channels", null=True, blank=True)
    model = models.CharField(max_length=128, default=DEFAULT_CHANNEL_MODEL)
    model_params = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_channel_org_code"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.code}"
