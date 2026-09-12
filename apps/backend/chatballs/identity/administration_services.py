from __future__ import annotations

import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from chatballs.i18n import t
from chatballs.i18n.languages import normalize_language
from chatballs.identity.logo_svg import SVG_CONTENT_TYPE, looks_like_svg, svg_is_safe
from chatballs.identity.models import Organization
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.storage import adjust_storage_usage
from chatballs.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)

MAX_LOGO_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class OrganizationSettingsInput:
    name: str
    timezone: str
    currency: str
    # Пустая строка — «как в установке»: организация не обязана выбирать язык,
    # и владелец, который его не трогал, не должен получить жёсткий русский
    # после того, как язык установки сменили.
    language: str = ""


def _validate_input(data: OrganizationSettingsInput) -> OrganizationSettingsInput:
    name = data.name.strip()
    timezone = data.timezone.strip()
    currency = data.currency.strip().upper()
    language = normalize_language(data.language)
    if data.language.strip() and not language:
        raise ValidationError({"language": t("settings.language_unsupported")})
    if not name:
        raise ValidationError({"name": t("admin.organization_name_required")})
    if len(name) > 255:
        raise ValidationError({"name": t("admin.name_too_long")})
    try:
        ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValidationError(
            {"timezone": t("admin.invalid_timezone")}
        ) from error
    if currency != "RUB":
        raise ValidationError(
            {"currency": t("admin.currency_rub_only")}
        )
    return OrganizationSettingsInput(
        name=name, timezone=timezone, currency=currency, language=language
    )


@transaction.atomic
def update_organization_settings(
    *,
    context: TenantContext,
    data: OrganizationSettingsInput,
) -> Organization:
    clean = _validate_input(data)
    organization = Organization.objects.select_for_update().get(
        pk=context.organization_id
    )
    organization.name = clean.name
    organization.timezone = clean.timezone
    organization.currency = clean.currency
    organization.language = clean.language
    organization.save(update_fields=["name", "timezone", "currency", "language"])
    return organization


def _image_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if looks_like_svg(data):
        return SVG_CONTENT_TYPE, ".svg"
    return None


@transaction.atomic
def replace_organization_logo(
    *,
    context: TenantContext,
    upload: UploadedFile,
) -> Organization:
    data = upload.read()
    if not data:
        raise ValidationError({"file": t("admin.choose_logo_file")})
    if len(data) > MAX_LOGO_BYTES:
        raise ValidationError({"file": t("admin.logo_too_large")})
    detected = _image_type(data)
    if detected is None:
        raise ValidationError({"file": t("admin.image_formats")})
    if detected[0] == SVG_CONTENT_TYPE and not svg_is_safe(data):
        # Скрипты, внешние ссылки и обработчики событий в логотипе не нужны:
        # файл отклоняется целиком, а не переписывается молча.
        raise ValidationError({"file": t("admin.svg_logo_unsafe")})
    content_type, suffix = detected
    organization = Organization.objects.select_for_update().get(
        pk=context.organization_id
    )
    previous_name = organization.logo.name
    previous_size = organization.logo_size
    reservation_key = f"organization-logo:{uuid.uuid4()}"
    reserve_storage(
        context=context,
        expected_bytes=len(data),
        idempotency_key=reservation_key,
    )
    try:
        organization.logo.save(
            f"logo{suffix}",
            ContentFile(data),
            save=False,
        )
        organization.logo_content_type = content_type
        organization.logo_size = len(data)
        organization.save(
            update_fields=["logo", "logo_content_type", "logo_size"],
        )
        if previous_name:
            organization.logo.storage.delete(previous_name)
            if previous_size:
                adjust_storage_usage(context=context, delta_bytes=-previous_size)
    except Exception:
        release_storage(context=context, idempotency_key=reservation_key)
        raise
    finalize_storage(
        context=context,
        idempotency_key=reservation_key,
        actual_bytes=len(data),
    )
    return organization


@transaction.atomic
def delete_organization_logo(*, context: TenantContext) -> Organization:
    organization = Organization.objects.select_for_update().get(
        pk=context.organization_id
    )
    previous_name = organization.logo.name
    previous_size = organization.logo_size
    organization.logo = ""
    organization.logo_content_type = ""
    organization.logo_size = 0
    organization.save(update_fields=["logo", "logo_content_type", "logo_size"])
    if previous_name:
        organization.logo.storage.delete(previous_name)
    if previous_size:
        adjust_storage_usage(context=context, delta_bytes=-previous_size)
    return organization
