from django.conf import settings
from django.db import models

from hub_platform.tenancy.models import TenantRelationModel

# Уведомления: событие создаётся один раз и адресуется аудитории; прочтение —
# персональное (NotificationRead). Фундамент под любые типы событий, не только чат.


class NotificationType(models.TextChoices):
    DIALOG_WAITING = "DIALOG_WAITING", "Диалог ждёт оператора"
    DIALOG_NEW_MESSAGE = "DIALOG_NEW_MESSAGE", "Новое сообщение в диалоге"
    # Задел на будущее (добавляются записью в реестр notifications.services.TYPE_META):
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED", "Платёж получен"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Проблема с платежом"
    RELEASE_PUBLISHED = "RELEASE_PUBLISHED", "Опубликован релиз агента"
    INTEGRATION_ERROR = "INTEGRATION_ERROR", "Ошибка интеграции"
    LIMIT_REACHED = "LIMIT_REACHED", "Достигнут лимит"


class NotificationLevel(models.TextChoices):
    INFO = "INFO", "Инфо"
    SUCCESS = "SUCCESS", "Успех"
    WARNING = "WARNING", "Предупреждение"
    CRITICAL = "CRITICAL", "Критично"


class NotificationAudience(models.TextChoices):
    ALL = "ALL", "Все"
    OWNER = "OWNER", "Владелец"
    OPERATORS = "OPERATORS", "Операторы"
    USER = "USER", "Конкретный пользователь"


class Notification(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="notifications")
    department = models.ForeignKey(
        "identity.Department",
        on_delete=models.PROTECT,
        related_name="notifications",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    level = models.CharField(max_length=16, choices=NotificationLevel.choices, default=NotificationLevel.INFO)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    # Диплинк по клику.
    target_route = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    audience = models.CharField(max_length=16, choices=NotificationAudience.choices, default=NotificationAudience.ALL)
    recipient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="direct_notifications")
    source_type = models.CharField(max_length=64, blank=True)
    source_id = models.CharField(max_length=64, blank=True)
    dedup_key = models.CharField(max_length=128, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "created_at"])]

    def __str__(self) -> str:
        return f"notif:{self.type}/{self.audience}"


class NotificationRead(TenantRelationModel):
    tenant_relation_fields = ("notification",)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notification", "user"], name="uniq_notification_read")]


def default_push_types() -> list[str]:
    # Дефолт: диалоговые события (новый диалог / ждёт оператора / новое сообщение).
    return [NotificationType.DIALOG_WAITING, NotificationType.DIALOG_NEW_MESSAGE]


class MessengerBinding(TenantRelationModel):
    """Привязка сотрудника к сервисному боту уведомлений (TG/MAX).

    Создаётся при подтверждении одноразового кода из профиля; уведомления
    доставляются в external_chat_id через транспорт интеграции."""

    tenant_relation_fields = ("integration",)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messenger_bindings")
    integration = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="messenger_bindings")
    external_chat_id = models.CharField(max_length=128)
    # Типы уведомлений, которые доставляются в мессенджер (подмножество NotificationType).
    push_types = models.JSONField(default=default_push_types, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["integration", "user"], name="uniq_binding_integration_user")]

    def __str__(self) -> str:
        return f"binding:{self.user_id}/{self.integration_id}"


class MessengerBindingCode(TenantRelationModel):
    tenant_relation_fields = ("integration",)
    # Одноразовый код привязки (deep-link ?start=<code>); TTL ~10 минут.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messenger_binding_codes")
    integration = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="messenger_binding_codes")
    code = models.CharField(max_length=32, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"binding-code:{self.user_id}/{self.integration_id}"
