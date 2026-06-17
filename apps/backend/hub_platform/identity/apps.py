from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "identity"
    name = "hub_platform.identity"
    verbose_name = "Identity and platform core"
