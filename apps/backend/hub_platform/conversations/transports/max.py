"""MAX bot transport (M2, ADR-HUB-0020).

Long polling for inbound updates and text sending. MAX (TamTam heritage) field
naming is not fully documented, so inbound parsing is defensive and the raw
update is logged so the live shape can be confirmed.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse

from hub_platform.conversations.transports.base import InboundMessage, first, request_json
from hub_platform.integrations.checks import DEFAULT_MAX_BASE_URL

logger = logging.getLogger(__name__)


def _base(integration) -> str:
    return (integration.config.get("base_url") or DEFAULT_MAX_BASE_URL).rstrip("/")


def _proxy(integration) -> str:
    return integration.config.get("proxy_url", "")


def _normalize(update: dict) -> InboundMessage | None:
    logger.info("MAX raw update: %s", json.dumps(update, ensure_ascii=False))
    update_type = update.get("update_type") or update.get("updateType")
    if update_type not in (None, "message_created"):
        return None
    msg = update.get("message") or update.get("payload") or {}
    inner = msg.get("body") or msg.get("message") or msg
    text = first(inner, "text") or first(msg, "text") or ""
    sender = msg.get("sender") or inner.get("sender") or {}
    user_id = first(sender, "user_id", "userId", "id") or first(msg, "from_id")
    recipient = msg.get("recipient") or msg.get("chat") or {}
    chat_id = first(recipient, "chat_id", "chatId")
    external_id = first(inner, "mid", "msgId", "seq") or first(update, "update_id", "updateId", "timestamp")
    if not text or user_id is None or external_id is None:
        return None
    return InboundMessage(
        external_id=str(external_id),
        user_id=str(user_id),
        chat_id="" if chat_id is None else str(chat_id),
        text=str(text),
        display_name=str(first(sender, "name", "display_name", default="")),
    )


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    token = integration.secret
    if not token:
        return [], integration.poll_marker
    params = {"timeout": 20, "limit": 100}
    if integration.poll_marker:
        params["marker"] = integration.poll_marker
    url = f"{_base(integration)}/updates?{urllib.parse.urlencode(params)}"
    try:
        data = request_json(url, headers={"Authorization": token, "Content-Type": "application/json"}, proxy_url=_proxy(integration))
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
        request_json(url, headers={"Authorization": token, "Content-Type": "application/json"}, method="POST", body={"text": text}, proxy_url=_proxy(integration))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        logger.warning("MAX send failed for integration %s: %s", integration.id, error)
        return False
