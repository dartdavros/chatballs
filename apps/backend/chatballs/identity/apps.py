from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "identity"
    name = "chatballs.identity"
    verbose_name = "Identity and platform core"

    def ready(self) -> None:
        from chatballs.identity import event_handlers  # noqa: F401  (register outbox handlers)
