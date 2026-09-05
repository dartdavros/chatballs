"""Email (IMAP/SMTP) transport (ADR-HUB-0035, SPEC-HUB-0025 §3.3–3.4).

Polling IMAP with a UID cursor in poll_marker («uidvalidity:last_uid»), replies
via SMTP into the same thread (Re:/In-Reply-To/References from the dialog's
transport_meta). One mailbox password (app password) serves both sides.
"""

from __future__ import annotations

import html
import imaplib
import logging
import re
import smtplib
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr

from django.conf import settings

from chatballs.conversations.html_sanitizer import sanitize_email_html
from chatballs.conversations.transports.base import InboundMessage

logger = logging.getLogger(__name__)

DEFAULT_IMAP_PORT = 993
DEFAULT_SMTP_PORT = 465

_TAG = re.compile(r"<[^>]+>")
_BLANK_LINES = re.compile(r"\n{3,}")


def _address(integration) -> str:
    return str(integration.config.get("email", "")).strip().lower()


def _imap_connect(integration) -> imaplib.IMAP4:
    host = str(integration.config.get("imap_host", "")).strip()
    port = int(integration.config.get("imap_port") or DEFAULT_IMAP_PORT)
    timeout = settings.CHATBALLS_AI_REQUEST_TIMEOUT
    use_ssl = integration.config.get("imap_ssl", True)
    client = imaplib.IMAP4_SSL(host, port, timeout=timeout) if use_ssl else imaplib.IMAP4(host, port, timeout=timeout)
    client.login(_address(integration), integration.secret)
    return client


def _html_to_text(markup: str) -> str:
    text = _TAG.sub(" ", re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", markup))
    return _BLANK_LINES.sub("\n\n", html.unescape(text)).strip()


def _body_text(message) -> str:
    plain = message.get_body(preferencelist=("plain",))
    if plain is not None:
        return str(plain.get_content()).strip()
    rich = message.get_body(preferencelist=("html",))
    return _html_to_text(str(rich.get_content())) if rich is not None else ""


def _body_html(message) -> str:
    rich = message.get_body(preferencelist=("html",))
    if rich is None:
        return ""
    return sanitize_email_html(str(rich.get_content()))


def _normalize(message, *, own_address: str, fallback_id: str) -> tuple[InboundMessage | None, str]:
    """Parse one RFC822 message → (InboundMessage | None, raw Message-ID)."""
    display_name, address = parseaddr(str(message.get("From", "")))
    address = address.strip().lower()
    # Собственные письма ящика (копии отправленного) диалогом не являются.
    if not address or address == own_address:
        return None, ""
    message_id = str(message.get("Message-ID", "")).strip()
    text = _body_text(message)
    content_html = _body_html(message)
    attachments = sum(1 for _ in message.iter_attachments())
    if attachments:
        # Вложения в первой итерации не принимаются (ADR-HUB-0035).
        note = f"[Вложения не поддерживаются: {attachments} файл(ов)]"
        text = f"{text}\n\n{note}".strip()
    if not text:
        return None, message_id
    inbound = InboundMessage(
        external_id=message_id or fallback_id,
        user_id=address,
        chat_id=address,
        text=text,
        content_html=content_html,
        display_name=str(display_name).strip() or address,
        thread_meta={"subject": str(message.get("Subject", "")).strip(), "last_message_id": message_id},
    )
    return inbound, message_id


def _status_value(client: imaplib.IMAP4, key: str) -> int:
    _, data = client.status("INBOX", f"({key})")
    match = re.search(rf"{key}\s+(\d+)", (data[0] or b"").decode("ascii", "replace"))
    return int(match.group(1)) if match else 0


def _parse_marker(marker: str) -> tuple[int, int]:
    try:
        validity, last_uid = marker.split(":", 1)
        return int(validity), int(last_uid)
    except (ValueError, AttributeError):
        return 0, 0


def poll_updates(integration) -> tuple[list[InboundMessage], str]:
    if not integration.secret or not integration.config.get("imap_host"):
        return [], integration.poll_marker
    try:
        client = _imap_connect(integration)
    except (imaplib.IMAP4.error, OSError, TimeoutError) as error:
        logger.warning("Email IMAP poll failed for integration %s: %s", integration.id, error)
        return [], integration.poll_marker
    try:
        client.select("INBOX", readonly=True)
        validity = _status_value(client, "UIDVALIDITY")
        next_uid = _status_value(client, "UIDNEXT")
        known_validity, last_uid = _parse_marker(integration.poll_marker)
        if validity != known_validity:
            # Первый запуск или смена UIDVALIDITY: курсор — на текущий конец
            # ящика, история не импортируется (SPEC-HUB-0025 §3.3).
            return [], f"{validity}:{max(next_uid - 1, 0)}"
        _, found = client.uid("SEARCH", None, f"UID {last_uid + 1}:*")
        # IMAP-диапазон N:* всегда включает старшее письмо — отсекаем уже виденные.
        uids = sorted(int(u) for u in (found[0] or b"").split() if int(u) > last_uid)
        messages: list[InboundMessage] = []
        for uid in uids:
            _, fetched = client.uid("FETCH", str(uid), "(RFC822)")
            raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
            if raw is None:
                continue
            parsed = message_from_bytes(raw, policy=policy.default)
            inbound, _ = _normalize(parsed, own_address=_address(integration), fallback_id=f"{validity}:{uid}")
            if inbound is not None:
                messages.append(inbound)
        new_marker = f"{validity}:{uids[-1]}" if uids else integration.poll_marker
        return messages, new_marker
    except (imaplib.IMAP4.error, OSError, TimeoutError) as error:
        logger.warning("Email IMAP poll failed for integration %s: %s", integration.id, error)
        return [], integration.poll_marker
    finally:
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def _thread_meta(integration, address: str) -> dict:
    from chatballs.conversations.models import Conversation

    conversation = (
        Conversation.objects.filter(connection=integration, external_chat_id=address)
        .order_by("-last_activity_at")
        .first()
    )
    return dict(conversation.transport_meta or {}) if conversation else {}


def send_text(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    target = (chat_id or user_id).strip().lower()
    host = str(integration.config.get("smtp_host", "")).strip()
    if not target or not host or not integration.secret:
        return False
    port = int(integration.config.get("smtp_port") or DEFAULT_SMTP_PORT)
    meta = _thread_meta(integration, target)

    outgoing = EmailMessage()
    outgoing["From"] = _address(integration)
    outgoing["To"] = target
    subject = str(meta.get("subject", "")).strip()
    outgoing["Subject"] = f"Re: {subject}" if subject and not subject.lower().startswith("re:") else (subject or "Re: Ваше обращение")
    last_message_id = str(meta.get("last_message_id", "")).strip()
    if last_message_id:
        outgoing["In-Reply-To"] = last_message_id
        outgoing["References"] = last_message_id
    outgoing.set_content(text)

    timeout = settings.CHATBALLS_AI_REQUEST_TIMEOUT
    try:
        if integration.config.get("smtp_ssl", True):
            client = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            client = smtplib.SMTP(host, port, timeout=timeout)
            client.starttls()
        with client:
            client.login(_address(integration), integration.secret)
            client.send_message(outgoing)
        return True
    except (smtplib.SMTPException, OSError, TimeoutError) as error:
        logger.warning("Email SMTP send failed for integration %s: %s", integration.id, error)
        return False
