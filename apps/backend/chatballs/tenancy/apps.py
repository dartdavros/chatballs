from django.apps import AppConfig


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatballs.tenancy"

    def ready(self) -> None:
        from chatballs.tenancy import storage_migration  # noqa: F401  (register outbox handler)
