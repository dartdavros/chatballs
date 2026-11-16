"""Customer messages; internal comments have separate storage and cursors."""

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models
from django.utils.functional import lazy

from chatballs.conversations.audience_managers import CustomerMessages
from chatballs.conversations.system_events import SystemEvent
from chatballs.conversations.upload_paths import (
    message_attachment_upload_path,
    message_audio_upload_path,
)
from chatballs.i18n import t
from chatballs.tenancy.models import TenantRelationModel


class MessageAuthor(models.TextChoices):
    CONTACT = "CONTACT", "Клиент"
    AI = "AI", "AI"
    OPERATOR = "OPERATOR", "Оператор"
    SYSTEM = "SYSTEM", lazy(t, str)("admin.actor_system")


class MessageKind(models.TextChoices):
    TEXT = "", "Текст"
    CONTACT_REQUEST = "contact_request", "Запрос контакта"
    CONTACT = "contact", "Контакт"
    VOICE = "voice", "Голосовое сообщение"
    FILE = "file", "Файл"


class AiTurnState(models.TextChoices):
    """Состояние хода AI по входящему сообщению.

    Ответ считается не в приёме, а отдельной ролью воркера
    (chatballs.conversations.ai_turn), поэтому у входящего появилось состояние.
    По нему видно, что ответ ещё считается — виджет показывает «печатает», — и
    по нему же повторная доставка события не приводит ко второму ответу.
    """

    NONE = "NONE", "Ход не нужен"
    PENDING = "PENDING", "Ожидает"
    RUNNING = "RUNNING", "Считается"
    DONE = "DONE", "Отвечено"
    FAILED = "FAILED", "Не удалось"


class TranscriptStatus(models.TextChoices):
    # Расшифровка голосового (дизайн-базлайн v2, кадр H): по кнопке, через
    # BYOK-провайдера организации (решение владельца 2026-09-04).
    NONE = "NONE", "Не расшифровано"
    READY = "READY", "Готова"
    FAILED = "FAILED", "Ошибка"


class Message(TenantRelationModel):
    tenant_relation_fields = ("conversation", "ai_reply_to")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.CASCADE, related_name="messages")
    author_type = models.CharField(max_length=16, choices=MessageAuthor.choices)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # Тип сообщения: обычный текст, запрос контакта (веб-виджет рисует форму
    # телефона), полученный контакт. Пустая строка = текст.
    kind = models.CharField(max_length=32, choices=MessageKind.choices, default=MessageKind.TEXT, blank=True)
    text = models.TextField(blank=True)
    # Системное событие: код и его параметры (имя оператора, длительность).
    # Пустой код — обычное сообщение либо системная запись, сделанная до
    # появления поля; такие показываются по сохранённому тексту.
    system_event = models.CharField(max_length=32, choices=SystemEvent.choices, blank=True, default="")
    system_params = models.JSONField(default=dict, blank=True)
    # Sanitized incoming email or an explicitly versioned outgoing snapshot.
    content_html = models.TextField(blank=True)
    format_version = models.PositiveSmallIntegerField(default=0)
    presentation = models.JSONField(default=dict, blank=True)
    delivery_representation = models.CharField(max_length=8, blank=True, default="")
    template_snapshot = models.JSONField(default=dict, blank=True)
    # Private route and acknowledged transport state; never serialized.
    ai_delivery = models.JSONField(default=dict, blank=True)
    ai_reply_to = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_reply",
    )
    # Голосовое сообщение (kind=VOICE): аудиофайл, длительность и расшифровка.
    audio = models.FileField(upload_to=message_audio_upload_path, max_length=512, blank=True)
    audio_content_type = models.CharField(max_length=64, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    transcript = models.TextField(blank=True)
    transcript_status = models.CharField(
        max_length=8, choices=TranscriptStatus.choices, default=TranscriptStatus.NONE
    )
    # Ход AI по этому сообщению: ожидает, считается, отвечено, не удалось.
    ai_turn_state = models.CharField(
        max_length=8, choices=AiTurnState.choices, default=AiTurnState.NONE
    )
    # Файл/фото (kind=FILE): вложение с исходным именем, типом и размером.
    attachment = models.FileField(upload_to=message_attachment_upload_path, max_length=512, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_content_type = models.CharField(max_length=128, blank=True)
    attachment_size = models.PositiveBigIntegerField(default=0)
    external_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    including_tests = models.Manager()
    objects = CustomerMessages()

    class Meta:
        default_manager_name = "objects"
        ordering = ["created_at"]
        indexes = [
            # Полнотекстовый поиск по сообщениям (поиск в списке диалогов).
            #
            # Конфигурация «russian» покрывает обе переписки, и второй индекс
            # под английский был бы тратой места: в ней asciiword отдан
            # english_stem, а word — russian_stem, поэтому английские слова
            # стеммятся английским стеммером, а русские русским. Обратное
            # неверно: «english» оставляет кириллицу без основы. Проверено
            # тестом conversations/test_search_language.py.
            GinIndex(
                SearchVector("text", config="russian"),
                name="conv_message_text_fts",
            ),
            # Окно истории идёт ровно по этому ключу: диалог → время → id.
            models.Index(
                fields=["conversation", "created_at", "id"], name="conv_message_window"
            ),
        ]

    def __str__(self) -> str:
        return f"msg:{self.conversation_id}/{self.author_type}"
