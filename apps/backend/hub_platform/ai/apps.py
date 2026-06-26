from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "ai"
    name = "hub_platform.ai"
    verbose_name = "AI agents, knowledge and releases"
