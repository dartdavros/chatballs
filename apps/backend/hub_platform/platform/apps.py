from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hub_platform.platform"
    verbose_name = "Platform control plane"
