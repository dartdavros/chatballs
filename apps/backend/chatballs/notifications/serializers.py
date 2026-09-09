from chatballs.i18n import t
from chatballs.notifications.models import Notification


def _text(key: str, stored: str, params: dict) -> str:
    """Фраза на языке запроса, если у записи есть ключ каталога.

    Уведомление адресовано аудитории, а не одному человеку: два оператора
    одной организации могут читать на разных языках, и записать готовую фразу
    в момент события нельзя. Записи, сделанные до появления ключей, приходят
    сохранённым текстом — переписывать историю задним числом не за что.
    """

    return t(key, **params) if key else stored


def notification_payload(notification: Notification, *, unread: bool) -> dict[str, object]:
    params = notification.text_params or {}
    return {
        "id": notification.id,
        "type": notification.type,
        "level": notification.level,
        "title": _text(notification.title_key, notification.title, params),
        "body": _text(notification.body_key, notification.body, params),
        "targetRoute": notification.target_route,
        "targetId": notification.target_id,
        "createdAt": notification.created_at.isoformat(),
        "unread": unread,
    }
