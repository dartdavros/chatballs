from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "ai"
    name = "chatballs.ai"
    verbose_name = "AI agents, knowledge and releases"
