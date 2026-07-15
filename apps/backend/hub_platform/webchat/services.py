import hashlib
import secrets
import uuid

from django.db import models, transaction

from hub_platform.conversations.ingest import ingest_inbound
from hub_platform.conversations.models import (
    ConnectionIdentity,
    Contact,
    Conversation,
    ControlMode,
    LifecycleState,
)
from hub_platform.conversations.transports.base import InboundMessage
from hub_platform.integrations.models import Integration, IntegrationProvider
from hub_platform.webchat.models import WebSession

DEFAULT_GREETING = "Здравствуйте! Готов помочь и ответить на вопросы. Чем можем помочь?"
DEFAULT_CONSENT = "Продолжая, вы соглашаетесь на обработку сообщений для ответа на обращение."
DEFAULT_ACCENT = "#1677ff"

_STATE = {ControlMode.AI: "ai", ControlMode.HUMAN: "operator", ControlMode.PAUSED: "waiting"}
_ROLE = {"CONTACT": "client", "AI": "ai", "OPERATOR": "operator", "SYSTEM": "system"}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def web_connection_for_channel(channel_code: str) -> Integration | None:
    matches = list(
        Integration.objects.select_related("channel")
        .filter(
            provider=IntegrationProvider.WEB,
            channel__code=channel_code,
            channel__is_active=True,
        )
        .order_by("id")[:2]
    )
    return matches[0] if len(matches) == 1 else None


def _host_allowed(integration: Integration, origin: str) -> bool:
    allowed = integration.config.get("allowed_domains") or []
    if not allowed:
        return True  # dev: пустой allowlist = разрешено
    if not origin:
        return False
    host = origin.split("//")[-1].split("/")[0].split(":")[0]
    return any(host == d or host.endswith("." + d) for d in allowed)


def public_config(channel_code: str, origin: str) -> dict:
    integration = web_connection_for_channel(channel_code)
    if integration is None or integration.channel_id is None:
        return {"available": False}
    if not _host_allowed(integration, origin):
        return {"available": False, "reason": "domain"}
    cfg = integration.config
    channel = integration.channel
    fallback = []
    for sib in Integration.objects.filter(channel=channel).exclude(id=integration.id):
        username = sib.config.get("bot_username")
        if sib.provider == IntegrationProvider.TELEGRAM and username:
            fallback.append({"label": "Написать в Telegram", "url": f"https://t.me/{username}"})
        elif sib.provider == IntegrationProvider.MAX and username:
            fallback.append({"label": "Написать в MAX", "url": ""})
    return {
        "available": True,
        "channel": channel.code,
        "title": cfg.get("title") or channel.name,
        "accent": cfg.get("accent") or DEFAULT_ACCENT,
        "greeting": cfg.get("greeting") or DEFAULT_GREETING,
        "consent": {"text": cfg.get("consent_text") or DEFAULT_CONSENT, "version": cfg.get("consent_version") or "v1"},
        "quickReplies": cfg.get("quick_replies") or [],
        "fallback": fallback,
    }


@transaction.atomic
def issue_session(channel_code: str) -> dict | None:
    integration = web_connection_for_channel(channel_code)
    if integration is None or integration.channel_id is None:
        return None
    session_id = uuid.uuid4().hex
    guest_name = f"Веб-гость · {session_id[:6]}"
    contact = Contact.objects.create(organization=integration.channel.organization, name=guest_name)
    identity = ConnectionIdentity.objects.create(
        contact=contact, connection=integration, external_user_id=session_id, display_name=guest_name
    )
    token = secrets.token_urlsafe(32)
    WebSession.objects.create(token_hash=_hash(token), connection=integration, identity=identity)
    return {"token": token, "sessionId": session_id}


def resolve_session(token: str) -> WebSession | None:
    if not token:
        return None
    return (
        WebSession.objects.select_related(
            "connection",
            "connection__channel",
            "connection__organization",
            "identity",
            "identity__contact",
        )
        .filter(
            token_hash=_hash(token),
            connection__organization_id=models.F("identity__contact__organization_id"),
            connection__channel__organization_id=models.F("connection__organization_id"),
        )
        .first()
    )


def post_message(session: WebSession, text: str) -> None:
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text=text,
        display_name=session.identity.display_name,
    )
    ingest_inbound(session.connection, inbound)


def normalize_phone(raw: str) -> str:
    """Нормализация телефона из формы виджета: только + и цифры, 10–15 цифр."""
    phone = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if phone.count("+") > 1 or (phone and "+" in phone[1:]):
        return ""
    digits = phone.lstrip("+")
    if not (10 <= len(digits) <= 15):
        return ""
    return phone


def post_contact(session: WebSession, phone: str) -> None:
    # Ответ клиента на запрос контакта: сообщение без текста, с телефоном —
    # ingest сохранит его в Contact.phone и подтвердит без AI-хода.
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text="",
        display_name=session.identity.display_name,
        phone=phone,
    )
    ingest_inbound(session.connection, inbound)


def _call_payload(session: WebSession) -> dict | None:
    # Приглашение на звонок для активной session (SPEC-HUB-0013 §7.1):
    # виджет получает его этим же поллингом, без отдельного realtime-канала.
    from hub_platform.calls.serializers import public_invite_payload
    from hub_platform.calls.services import webchat_active_call

    call = webchat_active_call(session.identity)
    if call is None:
        return None
    return public_invite_payload(call, call.invite.expires_at)


def messages_payload(session: WebSession, since: int) -> dict:
    conversation = (
        Conversation.objects.filter(
            channel=session.connection.channel, contact=session.identity.contact, lifecycle=LifecycleState.OPEN
        )
        .order_by("-last_activity_at")
        .first()
    )
    if conversation is None:
        return {"state": "ai", "lifecycle": LifecycleState.OPEN, "messages": [], "call": None}
    items = conversation.messages.filter(id__gt=since).order_by("created_at")
    return {
        "state": _STATE.get(conversation.control_mode, "ai"),
        "lifecycle": conversation.lifecycle,
        "messages": [
            {"id": m.id, "author": _ROLE.get(m.author_type, "ai"), "kind": m.kind, "text": m.text, "createdAt": m.created_at.isoformat()}
            for m in items
        ],
        "call": _call_payload(session),
    }
