from django.apps import AppConfig


class ChannelsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "channels"
    name = "chatballs.channels"
    verbose_name = "Processing channels (AI context)"
