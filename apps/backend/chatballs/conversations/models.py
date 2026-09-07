from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.db import models

from chatballs.tenancy.models import TenantRelationModel

# Минимальный домен диалогов (ADR-HUB-0001/0002/0003/0006). Состояние диалога
# разделено на независимые оси; перехват оператором — атомарный.


class Contact(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="contacts")
    name = models.CharField(max_length=255, blank=True)
    # Телефон приходит только через явный шаринг контакта (кнопка в TG/MAX,
    # форма в веб-чате) — автоматически мессенджеры его не отдают.
    phone = models.CharField(max_length=32, blank=True)
    # Внешний URL аватара контакта, если провайдер его отдаёт (например, MAX
    # присылает avatar_url в профиле отправителя). Telegram не отдаёт фото в
    # getUpdates, поэтому для него поле остаётся пустым. Хранится только URL —
    # само изображение живёт на стороне провайдера.
    avatar_url = models.URLField(max_length=512, blank=True, default="")
    # Карточка контакта (дизайн-базлайн v2, решение 5): описание, компания, город —
    # заполняет оператор.
    description = models.TextField(blank=True, default="")
    company = models.CharField(max_length=160, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    # Контакт, в который этот был объединён (ADR-HUB-0006). Строка не удаляется:
    # объединение обратимо, поэтому исходный контакт остаётся для разъединения.
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="merged_contacts",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name or f"contact:{self.id}"


class ContactMerge(models.Model):
    """Журнал объединения контактов (ADR-HUB-0006).

    Хранит, что именно переехало, чтобы объединение можно было развернуть
    обратно: перенесённые идентичности и диалоги и поля карточки, которые были
    заполнены из исходного контакта.
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="contact_merges")
    target = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="merges_in")
    source = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="merges_out")
    reason = models.TextField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    moved_identity_ids = models.JSONField(default=list, blank=True)
    moved_conversation_ids = models.JSONField(default=list, blank=True)
    filled_fields = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reverted_at = models.DateTimeField(null=True, blank=True)
    reverted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    revert_reason = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"merge:{self.source_id}->{self.target_id}"


class ConnectionIdentity(TenantRelationModel):
    tenant_relation_fields = ("contact", "connection")
    # Устойчивая идентичность контакта внутри конкретного подключения (ADR-HUB-0006).
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="identities")
    connection = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="identities")
    external_user_id = models.CharField(max_length=128)
    display_name = models.CharField(max_length=255, blank=True)
    # Публичный логин в мессенджере (@username в TG/MAX); пустой, если не задан.
    username = models.CharField(max_length=128, blank=True)
    # Когда подключение отдало подтверждённый телефон (кнопка «поделиться
    # контактом»). Только такая идентичность считается подтверждённой
    # (ADR-HUB-0006) — колонка «Статус» на вкладке «Идентификаторы».
    phone_verified_at = models.DateTimeField(null=True, blank=True, db_default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["connection", "external_user_id"], name="uniq_identity_connection_user"),
        ]

    def __str__(self) -> str:
        return f"{self.connection_id}:{self.external_user_id}"


class LifecycleState(models.TextChoices):
    OPEN = "OPEN", "Открыт"
    CLOSED = "CLOSED", "Закрыт"
    SPAM = "SPAM", "Спам"


class ConversationPriority(models.TextChoices):
    # Приоритет диалога (дизайн-базлайн v2, решение владельца 2026-09-04).
    HIGH = "HIGH", "Высокий"
    MEDIUM = "MEDIUM", "Средний"
    LOW = "LOW", "Низкий"
    NONE = "NONE", "Не задан"


class ConversationLabel(models.Model):
    """Метка диалога: цветной чип, общий словарь организации."""

    organization = models.ForeignKey(
        "identity.Organization", on_delete=models.PROTECT, related_name="conversation_labels"
    )
    name = models.CharField(max_length=60)
    # HEX-цвет чипа; палитру предлагает клиент.
    color = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("name"), "organization",
                name="uniq_conversation_label_org_name_ci",
            )
        ]

    def __str__(self) -> str:
        return f"label:{self.organization_id}/{self.name}"


class ControlMode(models.TextChoices):
    AI = "AI", "AI"
    HUMAN = "HUMAN", "Оператор"
    PAUSED = "PAUSED", "Пауза"


class ExpectedResponder(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Клиент"
    AI = "AI", "AI"
    OPERATOR = "OPERATOR", "Оператор"
    NOBODY = "NOBODY", "Никто"


class Conversation(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="conversations")
    channel = models.ForeignKey("channels.Channel", on_delete=models.PROTECT, related_name="conversations")
    connection = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="conversations", null=True, blank=True)
    # Единственный источник identity диалога — контакт. Авторизованный
    # in-product клиент (SupportIdentitySnapshot) удалён вместе с сущностью
    # Product (ADR-HUB-0045).
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="conversations", null=True, blank=True)
    # Внешний идентификатор чата (для отправки ответа в канал).
    external_chat_id = models.CharField(max_length=128, blank=True)
    # Транспортная мета диалога (ADR-HUB-0035): для email — тема исходного
    # письма и Message-ID последнего входящего (тредирование Re:/In-Reply-To).
    transport_meta = models.JSONField(default=dict, blank=True)
    lifecycle = models.CharField(max_length=16, choices=LifecycleState.choices, default=LifecycleState.OPEN)
    control_mode = models.CharField(max_length=16, choices=ControlMode.choices, default=ControlMode.AI)
    expected_responder = models.CharField(max_length=16, choices=ExpectedResponder.choices, default=ExpectedResponder.AI)
    # Группа видимости (ADR-HUB-0043): наследуется от group агента/канала при
    # создании, переносится вручную. NULL — диалог виден всем сотрудникам.
    group = models.ForeignKey(
        "identity.EmployeeGroup",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    # «Ответственный» (ADR-HUB-0043): видит диалог независимо от групп.
    assigned_operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_conversations")
    # Дизайн-базлайн v2: приоритет, метки и заметка оператора.
    priority = models.CharField(
        max_length=8, choices=ConversationPriority.choices, default=ConversationPriority.NONE
    )
    labels = models.ManyToManyField(ConversationLabel, blank=True, related_name="conversations")
    note = models.TextField(blank=True)
    # Кто и когда оставил заметку — подпись «Анна Ким · 2 сен» на карточке
    # контакта (дизайн-базлайн v2, кадр K3).
    note_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    note_updated_at = models.DateTimeField(null=True, blank=True, db_default=None)
    # «Удалить диалог» = архив (решение владельца): скрыт из списков, видят
    # только администраторы; данные не удаляются.
    archived_at = models.DateTimeField(null=True, blank=True)
    previous_conversation = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [models.Index(fields=["channel", "lifecycle"])]
        constraints = [
            # Диалог всегда принадлежит контакту.
            models.CheckConstraint(
                condition=models.Q(contact__isnull=False),
                name="conversation_requires_contact",
            ),
        ]

    def __str__(self) -> str:
        return f"conv:{self.id}/{self.lifecycle}/{self.control_mode}"


class ConversationRead(TenantRelationModel):
    """Персональная отметка прочтения диалога: до какого сообщения дочитал
    сотрудник. Обновляется при открытии диалога; бейдж непрочитанных в списке
    считается относительно этой отметки."""

    tenant_relation_fields = ("conversation",)

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_reads")
    last_read_message_id = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="uniq_conversation_read")]

    def __str__(self) -> str:
        return f"read:{self.conversation_id}/{self.user_id}@{self.last_read_message_id}"


class MessageAuthor(models.TextChoices):
    CONTACT = "CONTACT", "Клиент"
    AI = "AI", "AI"
    OPERATOR = "OPERATOR", "Оператор"
    SYSTEM = "SYSTEM", "Система"


class MessageKind(models.TextChoices):
    TEXT = "", "Текст"
    CONTACT_REQUEST = "contact_request", "Запрос контакта"
    CONTACT = "contact", "Контакт"
    VOICE = "voice", "Голосовое сообщение"
    FILE = "file", "Файл"


class TranscriptStatus(models.TextChoices):
    # Расшифровка голосового (дизайн-базлайн v2, кадр H): по кнопке, через
    # BYOK-провайдера организации (решение владельца 2026-09-04).
    NONE = "NONE", "Не расшифровано"
    READY = "READY", "Готова"
    FAILED = "FAILED", "Ошибка"


def message_audio_upload_path(instance: "Message", filename: str) -> str:
    import uuid
    from pathlib import Path

    suffix = Path(filename).suffix.lower() or ".ogg"
    organization = instance.conversation.organization
    return f"organizations/{organization.public_id}/voice/{uuid.uuid4().hex}{suffix}"


def message_attachment_upload_path(instance: "Message", filename: str) -> str:
    import uuid
    from pathlib import Path

    suffix = Path(filename).suffix.lower()[:16]
    organization = instance.conversation.organization
    return f"organizations/{organization.public_id}/files/{uuid.uuid4().hex}{suffix}"


class Message(TenantRelationModel):
    tenant_relation_fields = ("conversation",)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    author_type = models.CharField(max_length=16, choices=MessageAuthor.choices)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # Тип сообщения: обычный текст, запрос контакта (веб-виджет рисует форму
    # телефона), полученный контакт. Пустая строка = текст.
    kind = models.CharField(max_length=32, choices=MessageKind.choices, default=MessageKind.TEXT, blank=True)
    text = models.TextField(blank=True)
    # Санитизированный HTML входящего email. Остальные транспорты и исходящие
    # ответы используют plain text.
    content_html = models.TextField(blank=True)
    # Голосовое сообщение (kind=VOICE): аудиофайл, длительность и расшифровка.
    audio = models.FileField(upload_to=message_audio_upload_path, max_length=512, blank=True)
    audio_content_type = models.CharField(max_length=64, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    transcript = models.TextField(blank=True)
    transcript_status = models.CharField(
        max_length=8, choices=TranscriptStatus.choices, default=TranscriptStatus.NONE
    )
    # Файл/фото (kind=FILE): вложение с исходным именем, типом и размером.
    attachment = models.FileField(upload_to=message_attachment_upload_path, max_length=512, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_content_type = models.CharField(max_length=128, blank=True)
    attachment_size = models.PositiveBigIntegerField(default=0)
    external_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            # Полнотекстовый поиск по сообщениям (поиск в списке диалогов).
            GinIndex(
                SearchVector("text", config="russian"),
                name="conv_message_text_fts",
            ),
        ]

    def __str__(self) -> str:
        return f"msg:{self.conversation_id}/{self.author_type}"


class ReplyTemplate(models.Model):
    """Шаблон ответа оператора («/» в композере). Общий на организацию:
    редактируют администраторы, используют все сотрудники."""

    organization = models.ForeignKey(
        "identity.Organization", on_delete=models.PROTECT, related_name="reply_templates"
    )
    title = models.CharField(max_length=120)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("title"), "organization",
                name="uniq_reply_template_org_title_ci",
            )
        ]

    def __str__(self) -> str:
        return f"template:{self.organization_id}/{self.title}"
