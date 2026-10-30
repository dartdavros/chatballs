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
