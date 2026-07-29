from __future__ import annotations

import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from hub_platform.identity.models import Organization
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.storage import adjust_storage_usage
from hub_platform.tenancy.storage_quota import (
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


def _validate_input(data: OrganizationSettingsInput) -> OrganizationSettingsInput:
    name = data.name.strip()
    timezone = data.timezone.strip()
    currency = data.currency.strip().upper()
    if not name:
        raise ValidationError({"name": "Укажите название организации"})
    if len(name) > 255:
        raise ValidationError({"name": "Название не должно превышать 255 символов"})
    try:
        ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValidationError(
            {"timezone": "Укажите корректный часовой пояс"}
        ) from error
    if currency != "RUB":
        raise ValidationError(
            {"currency": "Поддерживается только российский рубль (RUB)"}
        )
    return OrganizationSettingsInput(name=name, timezone=timezone, currency=currency)


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
    organization.save(update_fields=["name", "timezone", "currency"])
    return organization


def _image_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


@transaction.atomic
def replace_organization_logo(
    *,
    context: TenantContext,
    upload: UploadedFile,
) -> Organization:
    data = upload.read()
    if not data:
        raise ValidationError({"file": "Выберите файл логотипа"})
    if len(data) > MAX_LOGO_BYTES:
        raise ValidationError({"file": "Размер логотипа не должен превышать 2 МБ"})
    detected = _image_type(data)
    if detected is None:
        raise ValidationError({"file": "Поддерживаются PNG, JPEG и WebP"})
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
