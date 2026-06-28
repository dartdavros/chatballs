"""MAX bot transport (M2a, ADR-HUB-0020).

Long polling for inbound updates and text sending. MAX (TamTam heritage) field
naming is not fully documented, so inbound parsing is defensive and the raw
update is logged so the live shape can be confirmed and pinned down quickly.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from django.conf import settings

from hub_platform.integrations.checks import DEFAULT_MAX_BASE_URL

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InboundMessage:
    external_id: str
    user_id: str
    chat_id: str
    text: str
    display_name: str


def _base(integration) -> str:
    return (integration.config.get("base_url") or DEFAULT_MAX_BASE_URL).rstrip("/")


def _request(url: str, *, token: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": token, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=settings.HUB_AI_REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _first(d: dict, *keys, default=None):
    for key in keys:
        value = d.get(key)
        if value not in (None, ""):
            return value
    return default


def _normalize(update: dict) -> InboundMessage | None:
    # Логируем сырой апдейт: на живом боте сразу видно реальную форму полей.
    logger.info("MAX raw update: %s", json.dumps(update, ensure_ascii=False))
    update_type = update.get("update_type") or update.get("updateType")
    if update_type not in (None, "message_created"):
        return None
    msg = update.get("message") or update.get("payload") or {}
    inner = msg.get("body") or msg.get("message") or msg
    text = _first(inner, "text") or _first(msg, "text") or ""
    sender = msg.get("sender") or inner.get("sender") or {}
    user_id = _first(sender, "user_id", "userId", "id") or _first(msg, "from_id")
    recipient = msg.get("recipient") or msg.get("chat") or {}
    chat_id = _first(recipient, "chat_id", "chatId")
    external_id = _first(inner, "mid", "msgId", "seq") or _first(update, "update_id", "updateId", "timestamp")
    if not text or user_id is None or external_id is None:
        return None
    return InboundMessage(
        external_id=str(external_id),
        user_id=str(user_id),
        chat_id="" if chat_id is None else str(chat_id),
        text=str(text),
        display_name=str(_first(sender, "name", "display_name", default="")),
    )


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    """Returns (messages, new_marker). Never raises — failures return ([], marker)."""
    token = integration.secret
    if not token:
        return [], integration.poll_marker
    params = {"timeout": 20, "limit": 100}
    if integration.poll_marker:
        params["marker"] = integration.poll_marker
    url = f"{_base(integration)}/updates?{urllib.parse.urlencode(params)}"
    try:
        data = _request(url, token=token)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        logger.warning("MAX poll failed for integration %s: %s", integration.id, error)
        return [], integration.poll_marker
    updates = data.get("updates") or []
    messages = [m for m in (_normalize(u) for u in updates) if m is not None]
    new_marker = data.get("marker")
    return messages, ("" if new_marker is None else str(new_marker))


def send_text(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    token = integration.secret
    if not token:
        return False
    query = {}
    if chat_id:
        query["chat_id"] = chat_id
    elif user_id:
        query["user_id"] = user_id
    url = f"{_base(integration)}/messages?{urllib.parse.urlencode(query)}"
    try:
        _request(url, token=token, method="POST", body={"text": text})
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        logger.warning("MAX send failed for integration %s: %s", integration.id, error)
        return False
