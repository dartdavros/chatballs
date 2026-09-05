from django.apps import AppConfig


class CallsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatballs.calls"
    verbose_name = "P2P calls"

    def ready(self) -> None:
        from chatballs.calls import event_handlers  # noqa: F401  (register outbox handlers)
