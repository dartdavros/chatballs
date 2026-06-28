from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "conversations"
    name = "hub_platform.conversations"
    verbose_name = "Conversations (contacts, dialogs, messages)"
