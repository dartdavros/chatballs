"""Conversation state and assignment, independent of message content."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from chatballs.tenancy.models import TenantRelationModel


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
    # Product (ADR-CHATBALLS-0045).
    contact = models.ForeignKey("conversations.Contact", on_delete=models.PROTECT, related_name="conversations", null=True, blank=True)
    # Внешний идентификатор чата (для отправки ответа в канал).
    external_chat_id = models.CharField(max_length=128, blank=True)
    # Транспортная мета диалога (ADR-CHATBALLS-0035): для email — тема исходного
    # письма и Message-ID последнего входящего (тредирование Re:/In-Reply-To).
    transport_meta = models.JSONField(default=dict, blank=True)
    lifecycle = models.CharField(max_length=16, choices=LifecycleState.choices, default=LifecycleState.OPEN)
    control_mode = models.CharField(max_length=16, choices=ControlMode.choices, default=ControlMode.AI)
    expected_responder = models.CharField(max_length=16, choices=ExpectedResponder.choices, default=ExpectedResponder.AI)
    # С какого момента диалог ждёт человека (chatballs.conversations.queue).
    # Не «последнее сообщение»: клиент, написавший повторно, ждёт не меньше, а
    # больше прежнего, и в очереди обязан оставаться выше, а не ниже.
    waiting_since = models.DateTimeField(null=True, blank=True)
    # Группа видимости (ADR-CHATBALLS-0043): наследуется от group агента/канала при
    # создании, переносится вручную. NULL — диалог виден всем сотрудникам.
    group = models.ForeignKey(
        "identity.EmployeeGroup",
        on_delete=models.SET_NULL,
        related_name="conversations",
        null=True,
        blank=True,
    )
    # «Ответственный» (ADR-CHATBALLS-0043): видит диалог независимо от групп.
    assigned_operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_conversations")
    # Когда назначили. С этого момента идёт срок личной очереди: не взял —
    # диалог возвращается в общую (chatballs.conversations.escalation).
    assigned_at = models.DateTimeField(null=True, blank=True)
    assignment_version = models.PositiveBigIntegerField(default=0, db_default=0, editable=False)
    ai_control_version = models.PositiveBigIntegerField(default=0, db_default=0, editable=False)
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
    # Время последнего сообщения — порядок инбокса. Отдельно от last_activity_at,
    # который двигают и служебные действия (перехват, возврат AI): по нему список
    # сортировать нельзя. У диалога без сообщений — время создания, поэтому поле
    # непустое и по нему работает и индекс, и курсор окна (api.pagination).
    last_message_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [
            models.Index(fields=["channel", "lifecycle"]),
            # Порядок инбокса: организация → свежесть. Раньше сортировка шла по
            # агрегату max(messages.created_at) и в индекс не ложилась.
            models.Index(
                fields=["organization", "-last_message_at", "-id"], name="conv_inbox_order"
            ),
            # Список контактов спрашивает по каждому контакту его свежий диалог
            # и число открытых — подзапросами по этой паре.
            models.Index(
                fields=["contact", "-last_activity_at"], name="conv_contact_recent"
            ),
            # Очередь к оператору: кто ждёт дольше всех и не дождался порога.
            models.Index(
                fields=["organization", "waiting_since"], name="conv_waiting_order"
            ),
        ]
        constraints = [
            # Диалог всегда принадлежит контакту.
            models.CheckConstraint(
                condition=models.Q(contact__isnull=False),
                name="conversation_requires_contact",
            ),
        ]

    def __str__(self) -> str:
        return f"conv:{self.id}/{self.lifecycle}/{self.control_mode}"

    def save(self, *args, **kwargs):
        existing = self.pk is not None
        super().save(*args, **kwargs)
        fields = kwargs.get("update_fields")
        if existing and (fields is None or set(fields) & {
            "assigned_operator", "assigned_operator_id", "assignment_version",
        }):
            # PostgreSQL owns this value, including for older claim/release
            # services; their HTTP result must expose the committed version.
            self.refresh_from_db(fields=["assignment_version"])
        if existing and (fields is None or set(fields) & {
            "control_mode", "assigned_operator", "assigned_operator_id", "channel", "channel_id", "lifecycle", "archived_at",
        }):
            self.refresh_from_db(fields=["ai_control_version"])


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
