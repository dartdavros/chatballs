from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "conversations"
    name = "chatballs.conversations"
    verbose_name = "Conversations (contacts, dialogs, messages)"

    def ready(self) -> None:
        # Свежесть диалога поддерживает сигнал: сообщения создаются в семи местах.
        from chatballs.conversations import signals  # noqa: F401
