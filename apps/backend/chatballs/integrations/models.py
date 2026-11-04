from django.db import models

from chatballs.identity.crypto import EncryptedCharField

# Интеграции: провайдеры (LLM) и подключения (боты/виджеты). ADR-CHATBALLS-0020.
# Привязка подключения к каналу обработки появляется в M1.


class IntegrationKind(models.TextChoices):
    LLM_PROVIDER = "LLM_PROVIDER", "LLM-провайдер"
    MESSENGER = "MESSENGER", "Подключение-мессенджер"
    # Внешний сервер: откуда агент берёт данные организации (SPEC-0023 R-1).
    EXTERNAL_SERVER = "EXTERNAL_SERVER", "Внешний сервер"
    # Сервис: подключение установленного адаптера (SPEC-0037 R-1). Какой это
    # сервис, хранит ServiceConnectionSettings, а не enum бренда.
    SERVICE = "SERVICE", "Сервис"


class IntegrationProvider(models.TextChoices):
    OPENROUTER = "OPENROUTER", "OpenRouter"
    CUSTOM = "CUSTOM", "Custom (OpenAI-compatible)"
    # Демо-провайдер: живой AI без ключей и сети — для знакомства с системой.
    DEMO = "DEMO", "Демо-провайдер (без ключа)"
    MAX = "MAX", "MAX"
    TELEGRAM = "TELEGRAM", "Telegram"
    VK = "VK", "ВКонтакте"
    WEB = "WEB", "Web-виджет"
    EMAIL = "EMAIL", "Email (IMAP/SMTP)"
    # Виды внешнего сервера: MCP-сервер с набором инструментов и HTTP-запрос —
    # один инструмент поверх REST API организации.
    MCP = "MCP", "MCP-сервер"
    HTTP = "HTTP", "HTTP-запрос"
    # Общий провайдер всех сервисных подключений: конкретный адаптер задаётся
    # ключом в настройках подключения (ADR-0038 п.2).
    ADAPTER = "ADAPTER", "Адаптер сервиса"


class IntegrationStatus(models.TextChoices):
    UNCHECKED = "UNCHECKED", "Не проверено"
    OK = "OK", "Подключено"
    ERROR = "ERROR", "Ошибка"


# Какой провайдер к какому роду относится.
PROVIDER_KIND = {
    IntegrationProvider.OPENROUTER: IntegrationKind.LLM_PROVIDER,
    # Custom — generic BYOK для любого OpenAI-compatible endpoint (ADR-CHATBALLS-0034).
    IntegrationProvider.CUSTOM: IntegrationKind.LLM_PROVIDER,
    IntegrationProvider.DEMO: IntegrationKind.LLM_PROVIDER,
    IntegrationProvider.MAX: IntegrationKind.MESSENGER,
    IntegrationProvider.TELEGRAM: IntegrationKind.MESSENGER,
    # Сообщество ВКонтакте: приём через Bots Long Poll, отправка messages.send.
    IntegrationProvider.VK: IntegrationKind.MESSENGER,
    IntegrationProvider.WEB: IntegrationKind.MESSENGER,
    # Email-ящик — транспорт диалогов наравне с ботами (ADR-CHATBALLS-0035).
    IntegrationProvider.EMAIL: IntegrationKind.MESSENGER,
    IntegrationProvider.MCP: IntegrationKind.EXTERNAL_SERVER,
    IntegrationProvider.HTTP: IntegrationKind.EXTERNAL_SERVER,
    IntegrationProvider.ADAPTER: IntegrationKind.SERVICE,
}


class Integration(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="integrations")
    kind = models.CharField(max_length=16, choices=IntegrationKind.choices)
    provider = models.CharField(max_length=16, choices=IntegrationProvider.choices)
    name = models.CharField(max_length=255)
    # Зашифрованный секрет: ключ провайдера или токен бота (Fernet).
    secret = EncryptedCharField(max_length=1024, blank=True)
    # Секретные заголовки внешнего сервера: JSON «имя → значение» (Fernet).
    # Имена и открытые заголовки лежат в config, наружу значения не отдаются.
    secret_headers = EncryptedCharField(max_length=16384, blank=True)
    # Несекретная конфигурация: base_url, модель по умолчанию и т.п.
    config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=IntegrationStatus.choices, default=IntegrationStatus.UNCHECKED)
    # Операционное состояние подключения. В отличие от status (результата
    # последней проверки), is_active явно разрешает или запрещает runtime.
    is_active = models.BooleanField(default=True)
    # Что разрешено в этой точке входа (админ, «Настройки → Голосовые и звонки»):
    # голосовые сообщения (запись в композере/виджете) и онлайн-звонки.
    voice_messages_enabled = models.BooleanField(default=True)
    audio_calls_enabled = models.BooleanField(default=True)
    video_calls_enabled = models.BooleanField(default=True)
    # Подключение (бот/виджет) привязано к каналу обработки.
    channel = models.ForeignKey("channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="connections")
    # Курсор Long Polling (marker MAX / offset Telegram).
    poll_marker = models.CharField(max_length=64, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    # Код причины последней ошибки внешнего сервера: по нему интерфейс выбирает
    # состояние (недоступен, неверная авторизация, адрес запрещён).
    last_error_code = models.CharField(max_length=32, blank=True)
    # Снимок инструментов MCP-сервера: имя, название, описание, схема параметров
    # и отметка «только чтение». Обновляется только по кнопке (SPEC-0023 R-2).
    tools = models.JSONField(default=list, blank=True)
    tools_refreshed_at = models.DateTimeField(null=True, blank=True)
    # Версия runtime-настроек LLM. Event-workers держат circuit breaker в своей
    # памяти и заменяют его после исправления конфигурации провайдера.
    runtime_revision = models.PositiveBigIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "provider", "name"], name="uniq_integration_org_provider_name"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.name}"


class ToolReadOnlyConfirmation(models.Model):
    """Подтверждение администратора, что MCP-инструмент только читает (SPEC-0023 R-6).

    Нужно инструменту, который сервер сам не отметил ``readOnlyHint``. Строка на
    инструмент одна: снятие её не удаляет, а записывает, кто и когда снял.
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="+")
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="tool_confirmations")
    tool_name = models.CharField(max_length=128)
    confirmed_by = models.ForeignKey(
        "identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField()
    revoked_by = models.ForeignKey(
        "identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["integration", "tool_name"], name="uniq_tool_confirmation"),
        ]

    def __str__(self) -> str:
        return f"confirmation:{self.integration_id}/{self.tool_name}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


# Модели сервисных подключений живут в своих модулях, а Django находит их
# здесь, в models приложения.
from chatballs.integrations.scenario_state.connections import (  # noqa: E402
    OAuthStateStatus,
    ServiceConnectionSettings,
    ServiceOAuthState,
)
from chatballs.integrations.scenario_state.files import ServiceFile  # noqa: E402
from chatballs.integrations.scenario_state.definitions import ScenarioConnection, ScenarioDefinition  # noqa: E402
from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey  # noqa: E402
from chatballs.integrations.scenario_state.synchronization import ServiceSynchronizationSettings, SynchronizationCheckpoint  # noqa: E402,F401
from chatballs.integrations.scenario_state.runs import ScenarioRun  # noqa: E402,F401
from chatballs.integrations.scenario_state.steps import ScenarioStep  # noqa: E402,F401
from chatballs.integrations.scenario_state.journal import RunJournalEntry  # noqa: E402,F401
from chatballs.integrations.scenario_state.limits import ConnectionExecutionLane  # noqa: E402,F401
from chatballs.integrations.scenario_state.retention import ScenarioRetentionPolicy, StepOperationalFile  # noqa: E402,F401
from chatballs.integrations.scenario_state.grants import ActionGrant  # noqa: E402,F401
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant  # noqa: E402,F401
from chatballs.integrations.scenario_state.progress import ScenarioBudget, ScenarioProgress  # noqa: E402,F401
from chatballs.integrations.scenario_state.waits import ScenarioWait  # noqa: E402,F401
from chatballs.integrations.scenario_state.receipts import EventReceipt  # noqa: E402,F401
from chatballs.integrations.scenario_state.automation import ScenarioAutomation, EventDelivery, EventSubscription, ScheduleCheckpoint, PollCursor  # noqa: E402,F401
from chatballs.integrations.scenario_state.entity_links import EntityLink, IntegrationEntityVersion  # noqa: E402,F401

__all__ = [
    "PROVIDER_KIND",
    "Integration",
    "IntegrationKind",
    "IntegrationProvider",
    "IntegrationStatus",
    "OAuthStateStatus",
    "ServiceConnectionSettings",
    "ServiceFile",
    "ScenarioConnection",
    "ScenarioDefinition",
    "ScenarioExternalKey",
    "ServiceSynchronizationSettings",
    "ServiceOAuthState",
    "ToolReadOnlyConfirmation",
]
