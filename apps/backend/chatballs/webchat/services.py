import hashlib
import secrets
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.db import models, transaction

from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    Conversation,
    ControlMode,
    LifecycleState,
    MessageKind,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.integrations.features import features_payload
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.models import WebChatWidget, WebSession

DEFAULT_GREETING = "Здравствуйте! Готов помочь и ответить на вопросы. Чем можем помочь?"
DEFAULT_CONSENT = "Продолжая, вы соглашаетесь на обработку сообщений для ответа на обращение."
DEFAULT_ACCENT = "#1677ff"

_STATE = {ControlMode.AI: "ai", ControlMode.HUMAN: "operator", ControlMode.PAUSED: "waiting"}
_ROLE = {"CONTACT": "client", "AI": "ai", "OPERATOR": "operator", "SYSTEM": "system"}


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def web_connection_for_channel(
    context: TenantContext,
    channel_code: str,
) -> Integration | None:
    matches = list(
        Integration.objects.select_related("channel")
        .filter(
            provider=IntegrationProvider.WEB,
            organization=context.organization,
            channel__code=channel_code,
            channel__organization=context.organization,
            channel__is_active=True,
        )
        .order_by("id")[:2]
    )
    return matches[0] if len(matches) == 1 else None


def origin_allowed(widget: WebChatWidget, origin: str) -> bool:
    allowed = widget.allowed_origins or []
    if not allowed:
        return bool(settings.DEBUG or settings.TESTING)
    if not origin:
        return False
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    normalized_origin = f"{parsed.scheme}://{parsed.netloc.lower()}"
    host = parsed.hostname.lower().rstrip(".")
    for raw_rule in allowed:
        rule = str(raw_rule).strip().lower().rstrip("/")
        if not rule:
            continue
        if "://" in rule and normalized_origin == rule:
            return True
        if rule.startswith("*."):
            suffix = rule[2:].rstrip(".")
            if host != suffix and host.endswith(f".{suffix}"):
                return True
        elif "://" not in rule and host == rule.rstrip("."):
            return True
    return False


def public_config(*, context: TenantContext, widget: WebChatWidget, origin: str) -> dict:
    integration = widget.integration
    if integration.channel_id is None:
        return {"available": False}
    if not origin_allowed(widget, origin):
        return {"available": False, "reason": "domain"}
    cfg = widget.presentation_config
    consent = widget.consent_config
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
        "widgetKey": widget.public_key,
        # Что разрешено в этой точке входа: виджет прячет микрофон при запрете.
        "features": features_payload(integration),
        "title": cfg.get("title") or channel.name,
        "accent": cfg.get("accent") or DEFAULT_ACCENT,
        "greeting": cfg.get("greeting") or DEFAULT_GREETING,
        "consent": {
            "text": consent.get("consent_text") or DEFAULT_CONSENT,
            "version": consent.get("consent_version") or "v1",
        },
        "quickReplies": cfg.get("quick_replies") or [],
        "fallback": fallback,
    }


@transaction.atomic
def issue_session(*, context: TenantContext, widget: WebChatWidget) -> dict | None:
    integration = widget.integration
    if integration is None or integration.channel_id is None:
        return None
    session_id = uuid.uuid4().hex
    guest_name = f"Гость · {session_id[:6]}"
    contact = Contact.objects.create(organization=integration.channel.organization, name=guest_name)
    identity = ConnectionIdentity.objects.create(
        organization=context.organization,
        contact=contact,
        connection=integration,
        external_user_id=session_id,
        display_name=guest_name,
    )
    token = secrets.token_urlsafe(32)
    WebSession.objects.create(
        organization=context.organization,
        token_hash=hash_session_token(token),
        connection=integration,
        widget=widget,
        identity=identity,
    )
    return {"token": token, "sessionId": session_id}


def resolve_session(
    *,
    context: TenantContext,
    token: str,
    session_id: int,
) -> WebSession | None:
    if not token:
        return None
    return (
        WebSession.objects.select_related(
            "connection",
            "connection__channel",
            "connection__organization",
            "widget",
            "identity",
            "identity__contact",
        )
        .filter(
            token_hash=hash_session_token(token),
            id=session_id,
            organization=context.organization,
            widget__organization=context.organization,
            widget__integration_id=models.F("connection_id"),
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
    _remember_widget(session)


def post_voice(session: WebSession, *, content: bytes, content_type: str, duration: int) -> None:
    """Голосовое из виджета: байты приходят телом запроса, скачивать нечего."""
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text="",
        display_name=session.identity.display_name,
        voice_content=content,
        voice_mime=content_type,
        voice_duration=duration,
    )
    ingest_inbound(session.connection, inbound)
    _remember_widget(session)


def post_file(session: WebSession, *, content: bytes, filename: str, content_type: str, caption: str = "") -> None:
    """Файл из виджета: байты приходят телом запроса, подпись — текстом."""
    from chatballs.conversations.transports.base import InboundFile, guess_content_type, safe_filename

    name = safe_filename(filename)
    mime = content_type or guess_content_type(name)
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text=caption,
        display_name=session.identity.display_name,
        files=(InboundFile(name=name, content_type=mime, size=len(content), content=content, is_image=mime.startswith("image/")),),
    )
    ingest_inbound(session.connection, inbound)
    _remember_widget(session)


def _remember_widget(session: WebSession) -> None:
    conversation = (
        Conversation.objects.filter(
            channel=session.connection.channel,
            contact=session.identity.contact,
            lifecycle=LifecycleState.OPEN,
        )
        .order_by("-last_activity_at")
        .first()
    )
    if conversation is not None:
        metadata = conversation.transport_meta or {}
        if "webChatWidgetId" not in metadata:
            conversation.transport_meta = {
                **metadata,
                "webChatWidgetId": session.widget_id,
            }
            conversation.save(update_fields=["transport_meta"])


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
    from chatballs.calls.serializers import public_invite_payload
    from chatballs.calls.services import webchat_active_call

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
            {
                "id": m.id,
                "author": _ROLE.get(m.author_type, "ai"),
                "kind": m.kind,
                "text": m.text,
                "createdAt": m.created_at.isoformat(),
                "durationSeconds": m.duration_seconds,
                "hasAudio": bool(m.audio),
                **(
                    {
                        "attachment": {
                            "name": m.attachment_name,
                            "contentType": m.attachment_content_type,
                            "size": m.attachment_size,
                            "available": bool(m.attachment),
                        }
                    }
                    if m.kind == MessageKind.FILE
                    else {}
                ),
            }
            for m in items
        ],
        "call": _call_payload(session),
    }
