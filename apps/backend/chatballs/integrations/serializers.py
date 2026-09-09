from urllib.parse import urlsplit, urlunsplit

from chatballs.integrations.models import Integration

# Пароль прокси наружу не отдаётся: в списке подключений его видел бы каждый,
# у кого есть право смотреть интеграции, а сам адрес попадал бы в логи и
# историю браузера вместе с ним. Пустое поле при сохранении означает
# «оставить прежний» — ровно как у секрета интеграции.
PROXY_PASSWORD_MASK = "••••••••"


def mask_proxy_url(url: str) -> str:
    """Адрес прокси без пароля: «socks5://user:••••••••@host:1080»."""
    if not url:
        return ""
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    userinfo = f"{parsed.username or ''}:{PROXY_PASSWORD_MASK}"
    return urlunsplit(
        (parsed.scheme, f"{userinfo}@{host}", parsed.path, parsed.query, parsed.fragment)
    )


def restore_proxy_password(submitted: str, stored: str) -> str:
    """Вернуть сохранённый пароль, если пришла маска того же прокси.

    Форма отправляет конфигурацию целиком, поэтому без этого замаскированное
    значение сохранилось бы вместо настоящего пароля и прокси перестал бы
    работать при первом же редактировании соседнего поля.
    """
    if not submitted or PROXY_PASSWORD_MASK not in submitted or not stored:
        return submitted
    new, old = urlsplit(submitted), urlsplit(stored)
    same_target = (
        new.scheme == old.scheme
        and (new.hostname or "") == (old.hostname or "")
        and new.port == old.port
        and (new.username or "") == (old.username or "")
    )
    if not same_target or not old.password:
        return submitted
    return stored


def secret_mask(secret: str) -> str:
    """Маска секрета для колонки «Секрет» (кадр N3): только публичный префикс
    ключа («sk-or-»), сам секрет наружу не отдаётся."""
    if not secret:
        return ""
    head = secret[:8]
    cut = head.rfind("-")
    prefix = head[: cut + 1] if cut > 0 else ""
    return f"{prefix}••••••••"


def integration_payload(integration: Integration) -> dict[str, object]:
    # Секрет не возвращаем; отдаём признак его наличия и маску префикса.
    payload = {
        "id": integration.id,
        "kind": integration.kind,
        "provider": integration.provider,
        "name": integration.name,
        "hasSecret": bool(integration.secret),
        "secretMasked": secret_mask(integration.secret),
        "isActive": integration.is_active,
        "config": {
            "baseUrl": integration.config.get("base_url", ""),
            "defaultModel": integration.config.get("default_model", ""),
            "transcriptionModel": integration.config.get("transcription_model", ""),
            "proxyUrl": mask_proxy_url(str(integration.config.get("proxy_url", ""))),
            "botId": integration.config.get("bot_id", ""),
            "botUsername": integration.config.get("bot_username", ""),
            "botName": integration.config.get("bot_name", ""),
            "purpose": integration.config.get("purpose", ""),
            "allowedOrigins": integration.config.get("allowed_domains", []),
            "title": integration.config.get("title", ""),
            "accent": integration.config.get("accent", ""),
            "greeting": integration.config.get("greeting", ""),
            "quickReplies": integration.config.get("quick_replies", []),
            "consentText": integration.config.get("consent_text", ""),
            "consentVersion": integration.config.get("consent_version", ""),
            # Email-подключение (ADR-CHATBALLS-0035).
            "email": integration.config.get("email", ""),
            "imapHost": integration.config.get("imap_host", ""),
            "imapPort": integration.config.get("imap_port", 993),
            "imapSsl": integration.config.get("imap_ssl", True),
            "smtpHost": integration.config.get("smtp_host", ""),
            "smtpPort": integration.config.get("smtp_port", 465),
            "smtpSsl": integration.config.get("smtp_ssl", True),
        },
        "channel": {"id": integration.channel.id, "code": integration.channel.code, "name": integration.channel.name} if integration.channel_id else None,
        "status": integration.status,
        "lastCheckedAt": integration.last_checked_at.isoformat() if integration.last_checked_at else None,
        "lastError": integration.last_error,
        "createdAt": integration.created_at.isoformat(),
        "updatedAt": integration.updated_at.isoformat(),
    }
    if integration.provider == "WEB":
        from chatballs.webchat.widgets import widget_for_integration, widget_payload

        payload["webChatWidget"] = widget_payload(widget_for_integration(integration))
    return payload
