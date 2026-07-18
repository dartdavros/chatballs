from django.conf import settings
from django.db import models

from hub_platform.tenancy.models import TenantRelationModel

# Минимальный домен диалогов (ADR-HUB-0001/0002/0003/0006). Состояние диалога
# разделено на независимые оси; перехват оператором — атомарный.


class Contact(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="contacts")
    name = models.CharField(max_length=255, blank=True)
    # Телефон приходит только через явный шаринг контакта (кнопка в TG/MAX,
    # форма в веб-чате) — автоматически мессенджеры его не отдают.
    phone = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name or f"contact:{self.id}"


class ConnectionIdentity(TenantRelationModel):
    tenant_relation_fields = ("contact", "connection")
    # Устойчивая идентичность контакта внутри конкретного подключения (ADR-HUB-0006).
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="identities")
    connection = models.ForeignKey("integrations.Integration", on_delete=models.PROTECT, related_name="identities")
    external_user_id = models.CharField(max_length=128)
    display_name = models.CharField(max_length=255, blank=True)
    # Публичный логин в мессенджере (@username в TG/MAX); пустой, если не задан.
    username = models.CharField(max_length=128, blank=True)
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
    # Источник identity диалога: sales Contact (лид/аноним) ИЛИ verified
    # SupportIdentitySnapshot (authenticated клиент продукта). ADR-HUB-0022:
    # sales-identity и support-identity разделены, ровно один источник на диалог.
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="conversations", null=True, blank=True)
    support_identity_snapshot = models.ForeignKey(
        "support.SupportIdentitySnapshot",
        on_delete=models.PROTECT,
        related_name="conversations",
        null=True,
        blank=True,
    )
    # Внешний идентификатор чата (для отправки ответа в канал).
    external_chat_id = models.CharField(max_length=128, blank=True)
    # Транспортная мета диалога (ADR-HUB-0035): для email — тема исходного
    # письма и Message-ID последнего входящего (тредирование Re:/In-Reply-To).
    transport_meta = models.JSONField(default=dict, blank=True)
    lifecycle = models.CharField(max_length=16, choices=LifecycleState.choices, default=LifecycleState.OPEN)
    control_mode = models.CharField(max_length=16, choices=ControlMode.choices, default=ControlMode.AI)
    expected_responder = models.CharField(max_length=16, choices=ExpectedResponder.choices, default=ExpectedResponder.AI)
    assigned_operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_conversations")
    previous_conversation = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [models.Index(fields=["channel", "lifecycle"])]
        constraints = [
            # Ровно один источник identity: sales Contact XOR SupportIdentitySnapshot.
            models.CheckConstraint(
                condition=(
                    models.Q(contact__isnull=True, support_identity_snapshot__isnull=False)
                    | models.Q(contact__isnull=False, support_identity_snapshot__isnull=True)
                ),
                name="conversation_exactly_one_identity",
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


class Message(TenantRelationModel):
    tenant_relation_fields = ("conversation",)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    author_type = models.CharField(max_length=16, choices=MessageAuthor.choices)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # Тип сообщения: обычный текст, запрос контакта (веб-виджет рисует форму
    # телефона), полученный контакт. Пустая строка = текст.
    kind = models.CharField(max_length=32, choices=MessageKind.choices, default=MessageKind.TEXT, blank=True)
    text = models.TextField(blank=True)
    external_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"msg:{self.conversation_id}/{self.author_type}"
