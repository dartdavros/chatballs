from django.apps import AppConfig


class CallsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hub_platform.calls"
    verbose_name = "P2P calls"

    def ready(self) -> None:
        from hub_platform.calls import event_handlers  # noqa: F401  (register outbox handlers)
