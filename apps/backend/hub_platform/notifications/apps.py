from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "notifications"
    name = "hub_platform.notifications"
    verbose_name = "Notifications"

    def ready(self) -> None:
        from hub_platform.notifications import event_handlers  # noqa: F401  (register outbox handlers)
