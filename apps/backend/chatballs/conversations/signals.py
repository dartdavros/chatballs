"""Сигналы домена диалогов.

Две задачи, и обе — про «после записи»:

* держать `Conversation.last_message_at` в согласии с лентой;
* оповещать открытые интерфейсы, что диалог изменился.

Сообщения создаются в семи местах (приём из каналов, ответ оператора,
голосовые, файлы, события звонков, демо-данные), а состояние диалога меняют
ещё и перехват, возврат AI, метки, приоритет, архив. Поэтому и то и другое
живёт в сигналах: иначе достаточно одного забытого места, чтобы диалог перестал
подниматься в инбоксе или чтобы у оператора не обновился экран.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from chatballs.conversations.models import Conversation, Message
from chatballs.conversations.realtime import (
    notify_conversation_changed,
    notify_inbox_changed,
)


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


@receiver(post_save, sender=Message, dispatch_uid="conversations.notify_message")
def notify_message(sender, instance: Message, created: bool, **kwargs) -> None:
    if not created:
        return
    notify_conversation_changed(
        instance.conversation_id, organization_id=instance.organization_id
    )


@receiver(post_save, sender=Conversation, dispatch_uid="conversations.notify_conversation")
def notify_conversation(sender, instance: Conversation, created: bool, **kwargs) -> None:
    """Перехват, возврат AI, метки, приоритет, архив — всё это запись строки."""
    if created:
        notify_inbox_changed(instance.organization_id)
        return
    notify_conversation_changed(instance.id, organization_id=instance.organization_id)
