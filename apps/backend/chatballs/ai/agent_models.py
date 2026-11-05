"""Конфигурация агента; помощь оператору независима от статуса автоответов."""

from django.db import models

from chatballs.ai.agent_config import (
    HISTORY_LIMIT_DEFAULT,
    AIAgentStatus,
    AnswerLanguage,
)
from chatballs.tenancy.models import TenantRelationModel


class AIAgent(TenantRelationModel):
    tenant_relation_fields = ("channel", "provider_integration", "transcription_integration", "synthesis_integration")
    channel = models.OneToOneField("channels.Channel", on_delete=models.CASCADE, related_name="ai_agent")
    # BYOK-секрет организации. Раньше жил на Channel, из-за
    # чего credential_mode и model были на агенте, а секрет — на канале: одно
    # решение в двух таблицах, и форма агента скрыто писала в канал.
    provider_integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.PROTECT,
        related_name="agents",
        null=True,
        blank=True,
    )
    # Чем расшифровывать голосовые. Обычно это тот же провайдер, что и отвечает,
    # но не всегда: модель, которая пишет ответы, может не уметь речь в текст
    # (у Anthropic и Yandex Foundation Models аудио-эндпоинта нет вовсе).
    # Пусто — расшифровка идёт к провайдеру ответов, как было.
    transcription_integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.PROTECT,
        related_name="transcribing_agents",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=AIAgentStatus.choices,
        default=AIAgentStatus.DRAFT,
    )
    assistance_enabled = models.BooleanField(default=False)
    lifecycle_version = models.PositiveIntegerField(default=0)
    # Модель ответов. Пусто — берётся модель по умолчанию из интеграции; так
    # агент следует за настройкой провайдера. Заполнено — решает агент: на одном
    # ключе живут разные агенты, и дорогая модель нужна не каждому.
    model = models.CharField(max_length=128, blank=True, default="")
    # Модель расшифровки голосовых. Пусто — модель из интеграции, которая
    # расшифровывает, а если и там пусто — whisper-1.
    transcription_model = models.CharField(max_length=128, blank=True, default="")
    transcription_language = models.CharField(max_length=16, blank=True, default="")
    synthesis_integration = models.ForeignKey(
        "integrations.Integration", on_delete=models.PROTECT, related_name="synthesizing_agents",
        null=True, blank=True,
    )
    synthesis_model = models.CharField(max_length=128, blank=True, default="")
    synthesis_voice = models.CharField(max_length=64, blank=True, default="")
    model_params = models.JSONField(default=dict, blank=True)
    # Сколько последних сообщений диалога уходит модели вместе с новым. Больше —
    # агент помнит длинный разговор, но каждый ответ дороже, а у локальной
    # модели с малым окном контекста хвост просто обрежется на её стороне.
    history_limit = models.PositiveSmallIntegerField(default=HISTORY_LIMIT_DEFAULT)
    # Язык ответов клиенту. По умолчанию агент отвечает на языке, на котором
    # к нему обратились: сигнал точный, лежит прямо в сообщении и не требует
    # настройки. База знаний при этом остаётся одноязычной — поиск ведёт
    # семантическая ветка (ai.retrieval), а эмбеддинги кроссязычные.
    #
    # Хранится либо режим (MIRROR, ORGANIZATION), либо код языка из
    # chatballs.i18n.LANGUAGE_CODES — для тех, кому нужен ровно один язык
    # независимо от того, на каком языке пришло сообщение.
    answer_language = models.CharField(
        max_length=16,
        default=AnswerLanguage.MIRROR,
    )
    # Инструкции из трёх частей; системный промпт собирается в этом порядке.
    persona = models.TextField(blank=True)  # кто он и что он
    tone = models.TextField(blank=True)  # как он должен говорить
    instructions = models.TextField(blank=True)  # правила работы
    # Выбор знаний из библиотеки организации.
    knowledge_items = models.ManyToManyField("ai.Knowledge", blank=True, related_name="agents")
    # Статьи портала поддержки остаются в support_portals: агент ссылается на
    # них, а не на копию, поэтому правка статьи сразу меняет ответы агента.
    portal_articles = models.ManyToManyField(
        "support_portals.PortalArticle",
        blank=True,
        related_name="agents",
    )
    allowed_tools = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.channel.code}:agent"

    @property
    def is_active(self) -> bool:
        return self.status == AIAgentStatus.ACTIVE

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.status = AIAgentStatus.ACTIVE if value else AIAgentStatus.DISABLED
