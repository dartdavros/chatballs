from django.conf import settings
from django.db import models

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


class NotificationRead(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="reads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notification", "user"], name="uniq_notification_read")]
