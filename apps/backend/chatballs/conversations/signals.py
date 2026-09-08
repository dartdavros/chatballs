"""Сигналы домена диалогов.

Единственная задача — держать `Conversation.last_message_at` в согласии с
лентой. Сообщения создаются в семи местах (приём из каналов, ответ оператора,
голосовые, файлы, события звонков, демо-данные), поэтому обновление живёт в
сигнале: иначе достаточно одного забытого места, чтобы диалог перестал
подниматься в инбоксе.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from chatballs.conversations.models import Conversation, Message


@receiver(post_save, sender=Message, dispatch_uid="conversations.touch_last_message_at")
def touch_last_message_at(sender, instance: Message, created: bool, **kwargs) -> None:
    """Свежесть диалога двигается только вперёд.

    Условие `__lt` защищает от задним числом импортированной переписки: старое
    сообщение не должно опускать диалог в инбоксе.
    """
    if not created or instance.created_at is None:
        return
    Conversation.objects.filter(
        id=instance.conversation_id, last_message_at__lt=instance.created_at
    ).update(last_message_at=instance.created_at)
