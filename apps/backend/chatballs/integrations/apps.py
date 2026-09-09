from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "integrations"
    name = "chatballs.integrations"
    verbose_name = "Integrations: providers and connections"
