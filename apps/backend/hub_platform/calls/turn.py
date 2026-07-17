from __future__ import annotations

import base64
import hashlib
import hmac
import time

from django.conf import settings


def turn_credentials(*, label: str = "hub", now: int | None = None) -> tuple[str, str]:
    """Краткоживущие TURN REST credentials для Coturn (SPEC-HUB-0013 §11).

    Схема coturn `use-auth-secret`:
        username   = "<expiry_unix_ts>:<label>"
        credential = base64(HMAC-SHA1(static-auth-secret, username))

    Coturn принимает пару, пока не истёк expiry в username и подпись совпадает с
    его `static-auth-secret`. Секрет (`CUS_CALL_TURN_SECRET`) общий с сервисом
    coturn и наружу не отдаётся — клиент получает только производные credentials.
    """
    moment = int(time.time()) if now is None else int(now)
    expiry = moment + settings.CUS_CALL_TURN_TTL_SECONDS
    username = f"{expiry}:{label}"
    digest = hmac.new(
        settings.CUS_CALL_TURN_SECRET.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    credential = base64.b64encode(digest).decode("ascii")
    return username, credential
