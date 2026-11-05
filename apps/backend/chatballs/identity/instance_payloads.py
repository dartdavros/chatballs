"""Public instance settings projection; credentials never leave the server."""
from django.conf import settings

from chatballs.i18n.languages import DEFAULT_LANGUAGE, LANGUAGES
from chatballs.identity.instance_settings import (
    InstanceSettings,
    default_turn_urls,
    format_address,
    public_base_url,
)


def instance_payload(row: InstanceSettings) -> dict:
    return {
        # Адрес целиком, с портом, если он не схемы: так его и вписывают.
        "publicHost": format_address(row.public_host, row.public_port),
        "publicScheme": row.public_scheme or "http",
        "publicUrl": public_base_url(),
        # Язык экранов, где организации ещё нет: логин, сброс пароля, мастер.
        "defaultLanguage": row.default_language or DEFAULT_LANGUAGE,
        "languages": [{"code": code, "label": label} for code, label in LANGUAGES],
        "updatedAt": row.updated_at,
        "email": {
            "host": row.email_host,
            "port": row.email_port,
            "user": row.email_user,
            # Пароль наружу не возвращается: пустое поле при сохранении
            # означает «оставить прежний».
            "hasPassword": bool(row.email_password),
            "useTls": row.email_use_tls,
            "from": row.email_from,
            "configured": bool(row.email_host),
        },
        "turn": {
            # Секрет общий с coturn и лежит в томе секретов: наружу не отдаём
            # и в настройках не показываем — вводить его человеку не нужно.
            #
            # Адреса показываются действующие: пока владелец их не менял, это
            # relay коробки на адресе установки. Пустое поле означало бы, что
            # звонки через relay не работают, пока человек что-то впишет, —
            # а они работают сразу после установки.
            "urls": [line for line in row.turn_urls.splitlines() if line.strip()]
            or default_turn_urls(),
            "ttlSeconds": row.turn_ttl_seconds,
            "secretReady": bool(settings.CHATBALLS_CALL_TURN_SECRET),
        },
    }
