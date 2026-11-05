"""Выдача, разрешение и срок жизни анонимных сессий веб-чата."""

import hashlib
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from chatballs.conversations.models import ConnectionIdentity, Contact
from chatballs.i18n import customer_language, t
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.models import WebChatWidget, WebSession


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


@transaction.atomic
def issue_session(
    *, context: TenantContext, widget: WebChatWidget, fields: object = None,
    pre_chat_fields: object = None, consent_version: object = None,
) -> dict | None:
    integration = widget.integration
    if integration is None or integration.channel_id is None:
        return None
    if consent_version is not None:
        from chatballs.webchat.consent import validate_acceptance

        validate_acceptance(widget, consent_version, pre_chat_fields)
    session_id = uuid.uuid4().hex
    guest_name = t(
        "webchat.guest_name",
        code=session_id[:6],
        language=customer_language(integration.channel.organization),
    )
    contact = Contact.objects.create(organization=integration.channel.organization, name=guest_name)
    identity = ConnectionIdentity.objects.create(
        organization=context.organization,
        contact=contact,
        connection=integration,
        external_user_id=session_id,
        display_name=guest_name,
    )
    token = secrets.token_urlsafe(32)
    session = WebSession.objects.create(
        organization=context.organization,
        token_hash=hash_session_token(token),
        connection=integration,
        widget=widget,
        identity=identity,
    )
    if fields is not None or pre_chat_fields is not None:
        from chatballs.webchat.site_fields import save_site_fields

        # Форма перекрывает данные сайта до проверки: невалидное значение
        # формы не должно незаметно восстанавливать прежнее значение с сайта.
        values = dict(fields) if isinstance(fields, dict) else {}
        if fields is not None and not isinstance(fields, dict):
            save_site_fields(session, fields)
        if isinstance(pre_chat_fields, dict):
            values.update(pre_chat_fields)
        elif pre_chat_fields is not None:
            save_site_fields(session, pre_chat_fields)
        save_site_fields(session, values)
    if consent_version is not None:
        from chatballs.webchat.consent import record_acceptance

        record_acceptance(session, version=consent_version, fields=pre_chat_fields)
    return {"token": token, "sessionId": session_id}


def resolve_session(
    *,
    context: TenantContext,
    token: str,
    session_id: int,
) -> WebSession | None:
    if not token:
        return None
    session = (
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
            last_seen_at__gt=timezone.now() - _session_idle_ttl(),
        )
        .first()
    )
    if session is not None:
        _touch_session(session)
    return session


def _session_idle_ttl() -> timedelta:
    return timedelta(seconds=settings.CHATBALLS_WEBCHAT_SESSION_IDLE_SECONDS)


# Отметку активности обновляем редко: виджет опрашивает ленту раз в 2.5 с, и
# запись на каждый опрос — это UPDATE строки сессии четыре раза в минуту на
# каждую открытую вкладку. Час загрубления на сроке в недели ничего не решает.
SESSION_TOUCH_THROTTLE = timedelta(hours=1)


def _touch_session(session: WebSession) -> None:
    if timezone.now() - session.last_seen_at >= SESSION_TOUCH_THROTTLE:
        # last_seen_at — auto_now, значение проставит сам Django.
        session.save(update_fields=["last_seen_at"])

