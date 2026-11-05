from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "integrations"
    name = "chatballs.integrations"
    verbose_name = "Integrations: providers and connections"

    def ready(self) -> None:
        # Описания установленных адаптеров проверяются при старте: ошибка
        # в описании видна сразу, а не при первом подключении (SPEC-0037 R-3).
        from chatballs.integrations.adapters.registry import default_registry

        default_registry()
        from chatballs.integrations.automation_events import (  # noqa: F401
            callbacks,
            entity_versions,  # noqa: F401
            fanout,
            native_facts,
            polling,
            replies,
        )
        from chatballs.integrations.execution import (
            ai_deadlines,  # noqa: F401
            cancellation,  # noqa: F401
            retention,  # noqa: F401
            worker,  # noqa: F401
        )
        from chatballs.integrations.scenarios import synchronization_runtime  # noqa: F401
