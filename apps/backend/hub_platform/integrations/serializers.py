from hub_platform.integrations.models import Integration


def integration_payload(integration: Integration) -> dict[str, object]:
    # Секрет не возвращаем; отдаём только признак его наличия.
    return {
        "id": integration.id,
        "kind": integration.kind,
        "provider": integration.provider,
        "name": integration.name,
        "hasSecret": bool(integration.secret),
        "config": {
            "baseUrl": integration.config.get("base_url", ""),
            "defaultModel": integration.config.get("default_model", ""),
            "proxyUrl": integration.config.get("proxy_url", ""),
            "botId": integration.config.get("bot_id", ""),
            "botUsername": integration.config.get("bot_username", ""),
            "botName": integration.config.get("bot_name", ""),
            "purpose": integration.config.get("purpose", ""),
            # Email-подключение (ADR-HUB-0035).
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
