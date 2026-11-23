"""Shared instance settings commands with the original field semantics."""
from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.i18n import t
from chatballs.i18n.languages import DEFAULT_LANGUAGE, normalize_language
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.instance_payloads import instance_payload
from chatballs.identity.instance_settings import (
    InstanceSettings,
    format_address,
    invalidate_cache,
    split_address,
)
from chatballs.integrations.action_catalog.authority import (
    require_instance,
    require_platform_settings,
)
from chatballs.support_portals.addressing import validate_domain

SCHEMES = ("http", "https")


def read(user):
    require_instance(user, read=True)
    return CommandOutcome({"instance": instance_payload(InstanceSettings.load())})


@transaction.atomic
def update(user, body):
    user = require_platform_settings(user)
    if isinstance(body, dict) and "turn" in body:
        require_instance(user)
    row = InstanceSettings.load()
    row = InstanceSettings.objects.select_for_update().get(pk=row.pk)
    body = body if isinstance(body, dict) else {}
    errors: dict[str, str] = {}

    fields = ["updated_at"]
    if "publicHost" in body or "publicScheme" in body:
        fields += _update_public_address(row, body, errors)

    if "defaultLanguage" in body:
        raw_language = str(body["defaultLanguage"]).strip()
        language = normalize_language(raw_language)
        if raw_language and not language:
            errors["defaultLanguage"] = t("settings.language_unsupported")
        row.default_language = language or DEFAULT_LANGUAGE
        fields.append("default_language")

    external_checks = body.get("externalChecksEnabled", row.external_checks_enabled)
    if not isinstance(external_checks, bool):
        errors["externalChecksEnabled"] = t("api.boolean_required")

    if errors:
        return CommandOutcome(
            {"detail": next(iter(errors.values())), "errors": errors}, status=400
        )

    if external_checks != row.external_checks_enabled:
        row.external_checks_enabled = external_checks
        row.external_checks_revision += 1
        fields += ["external_checks_enabled", "external_checks_revision"]

    email = body.get("email")
    if isinstance(email, dict):
        row.email_host = str(email.get("host", row.email_host)).strip()
        row.email_user = str(email.get("user", row.email_user)).strip()
        row.email_from = str(email.get("from", row.email_from)).strip()
        row.email_use_tls = bool(email.get("useTls", row.email_use_tls))
        try:
            row.email_port = int(email.get("port", row.email_port))
        except (TypeError, ValueError):
            return CommandOutcome(
                {"detail": t("settings.port_is_number"), "errors": {"emailPort": t("settings.port_is_number")}},
                status=400,
            )
        # Пустой пароль означает «оставить прежний»: наружу он не отдаётся.
        password = str(email.get("password", ""))
        if password:
            row.email_password = password
        fields += [
            "email_host",
            "email_port",
            "email_user",
            "email_password",
            "email_use_tls",
            "email_from",
        ]

    turn = body.get("turn")
    if isinstance(turn, dict):
        urls = turn.get("urls", [])
        if isinstance(urls, list):
            row.turn_urls = sep_join(urls)
        try:
            row.turn_ttl_seconds = max(60, int(turn.get("ttlSeconds", row.turn_ttl_seconds)))
        except (TypeError, ValueError):
            return CommandOutcome(
                {"detail": t("settings.ttl_is_seconds"),
                 "errors": {"turnTtlSeconds": t("settings.seconds_number")}},
                status=400,
            )
        fields += ["turn_urls", "turn_ttl_seconds"]

    row.save(update_fields=fields)
    invalidate_cache()
    if "external_checks_revision" in fields:
        from chatballs.realtime import publish
        from chatballs.updates.announcement_state import ANNOUNCEMENT_GROUP

        transaction.on_commit(lambda: publish(ANNOUNCEMENT_GROUP, {"type": "announcements.changed"}))
    return CommandOutcome({"instance": instance_payload(row)})


def _update_public_address(row: InstanceSettings, body: dict, errors: dict[str, str]) -> list[str]:
    scheme = str(body.get("publicScheme", row.public_scheme or "http")).lower()
    if scheme not in SCHEMES:
        errors["publicScheme"] = t("settings.http_or_https")

    # Владелец может вставить целый URL. Берём хост и порт, отбрасываем путь.
    raw_host = str(body.get("publicHost", format_address(row.public_host, row.public_port))).strip()
    if "//" in raw_host:
        raw_host = raw_host.split("//", 1)[1]
    parsed = split_address(raw_host.split("/", 1)[0], scheme)
    if parsed is None:
        errors["publicHost"] = t("settings.invalid_port")
        return []
    host, port = parsed
    if not host:
        errors["publicHost"] = t("settings.address_required")
    elif not _looks_like_ipv4(host):
        try:
            validate_domain(host)
        except ValidationError:
            errors["publicHost"] = t("settings.invalid_address")

    # Прежний адрес продолжает работать после смены хоста.
    if host != row.public_host:
        row.previous_public_host = row.public_host
    row.public_host = host
    row.public_port = port
    row.public_scheme = scheme
    return ["public_host", "public_port", "public_scheme", "previous_public_host"]


def _looks_like_ipv4(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)


def sep_join(urls) -> str:
    """Адреса TURN хранятся строками: по одному на строку."""

    lines = [str(item).strip() for item in urls if str(item).strip()]
    return chr(10).join(lines)
