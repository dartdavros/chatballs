from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "ai"
    name = "hub_platform.ai"
    verbose_name = "AI agents, knowledge and releases"

    def ready(self) -> None:
        from hub_platform.ai import signals  # noqa: F401  (connect product->agent invariant)
