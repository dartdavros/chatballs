from django.db import models

from hub_platform.identity.crypto import EncryptedCharField

# Интеграции: провайдеры (LLM) и подключения (боты/виджеты). ADR-HUB-0020.
# Привязка подключения к каналу обработки появляется в M1 (ADR-HUB-0019).


class IntegrationKind(models.TextChoices):
    LLM_PROVIDER = "LLM_PROVIDER", "LLM-провайдер"
    MESSENGER = "MESSENGER", "Подключение-мессенджер"


class IntegrationProvider(models.TextChoices):
    OPENROUTER = "OPENROUTER", "OpenRouter"
    CUSTOM = "CUSTOM", "Custom (OpenAI-compatible)"
    MAX = "MAX", "MAX"
    TELEGRAM = "TELEGRAM", "Telegram"
    WEB = "WEB", "Web-виджет"
    EMAIL = "EMAIL", "Email (IMAP/SMTP)"


class IntegrationStatus(models.TextChoices):
    UNCHECKED = "UNCHECKED", "Не проверено"
    OK = "OK", "Подключено"
    ERROR = "ERROR", "Ошибка"


# Какой провайдер к какому роду относится.
PROVIDER_KIND = {
    IntegrationProvider.OPENROUTER: IntegrationKind.LLM_PROVIDER,
    # Custom — generic BYOK для любого OpenAI-compatible endpoint (ADR-HUB-0034).
    IntegrationProvider.CUSTOM: IntegrationKind.LLM_PROVIDER,
    IntegrationProvider.MAX: IntegrationKind.MESSENGER,
    IntegrationProvider.TELEGRAM: IntegrationKind.MESSENGER,
    IntegrationProvider.WEB: IntegrationKind.MESSENGER,
    # Email-ящик — транспорт диалогов наравне с ботами (ADR-HUB-0035).
    IntegrationProvider.EMAIL: IntegrationKind.MESSENGER,
}


class Integration(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="integrations")
    kind = models.CharField(max_length=16, choices=IntegrationKind.choices)
    provider = models.CharField(max_length=16, choices=IntegrationProvider.choices)
    name = models.CharField(max_length=255)
    # Зашифрованный секрет: ключ провайдера или токен бота (Fernet).
    secret = EncryptedCharField(max_length=1024, blank=True)
    # Несекретная конфигурация: base_url, модель по умолчанию и т.п.
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=IntegrationStatus.choices, default=IntegrationStatus.UNCHECKED)
    # Подключение (бот/виджет) привязано к каналу обработки (ADR-HUB-0019, M2).
    channel = models.ForeignKey("channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="connections")
    # Курсор Long Polling (marker MAX / offset Telegram).
    poll_marker = models.CharField(max_length=64, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "provider", "name"], name="uniq_integration_org_provider_name"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.name}"
