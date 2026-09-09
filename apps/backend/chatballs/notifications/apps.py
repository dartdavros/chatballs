from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "notifications"
    name = "chatballs.notifications"
    verbose_name = "Notifications"

    def ready(self) -> None:
        from chatballs.notifications import event_handlers  # noqa: F401  (register outbox handlers)
