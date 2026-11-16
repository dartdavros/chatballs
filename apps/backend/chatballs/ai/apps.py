from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "ai"
    name = "chatballs.ai"
    verbose_name = "AI agents, knowledge and releases"

    def ready(self):
        from chatballs.ai.external_agents import (
            event_handlers,  # noqa: F401
            notice_models,  # noqa: F401
            operation_models,  # noqa: F401
            test_models,  # noqa: F401
        )
