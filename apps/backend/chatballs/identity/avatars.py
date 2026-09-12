"""Фото сотрудников (дизайн-базлайн v2).

Ссылка на фото строится от организации, в которой на него смотрят: файл
отдаёт тенантный эндпоинт, доступный любому участнику организации. Своё фото
в сессии — через профиль. В URL добавлен «хвост» имени файла, чтобы браузер
не показывал старое фото после замены.
"""

from __future__ import annotations

import functools
import hashlib
import uuid

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.models import HumanUser

MAX_AVATAR_BYTES = 2 * 1024 * 1024


def _version(user: HumanUser) -> str:
    return hashlib.sha1(user.avatar.name.encode("utf-8")).hexdigest()[:8]


def user_avatar_url(user: HumanUser | None, organization_public_id) -> str | None:
    if user is None or not user.avatar:
        return None
    return (
        f"/api/v1/organizations/{organization_public_id}/employees/{user.id}/avatar/"
        f"?v={_version(user)}"
    )


@functools.lru_cache(maxsize=4096)
def organization_public_id(organization_id: int) -> str:
    """public_id организации по id — неизменяем, поэтому кэшируется."""
    from chatballs.identity.models import Organization

    return str(Organization.objects.values_list("public_id", flat=True).get(pk=organization_id))


def user_avatar_url_in(user: HumanUser | None, organization_id: int) -> str | None:
    return user_avatar_url(user, organization_public_id(organization_id)) if user is not None else None


def own_avatar_url(user: HumanUser) -> str | None:
    if not user.avatar:
        return None
    return f"/api/v1/auth/profile/avatar/?v={_version(user)}"


def image_type(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def replace_user_avatar(user: HumanUser, upload: UploadedFile) -> HumanUser:
    data = upload.read()
    if not data:
        raise ValidationError({"file": t("profile.choose_photo_file")})
    if len(data) > MAX_AVATAR_BYTES:
        raise ValidationError({"file": t("profile.photo_too_large")})
    detected = image_type(data)
    if detected is None:
        raise ValidationError({"file": t("admin.image_formats")})
    content_type, suffix = detected
    return set_user_avatar(user, data, content_type, suffix)


def set_user_avatar(user: HumanUser, data: bytes, content_type: str, suffix: str) -> HumanUser:
    previous = user.avatar.name
    user.avatar.save(f"avatar-{uuid.uuid4()}{suffix}", ContentFile(data), save=False)
    user.avatar_content_type = content_type
    user.save(update_fields=["avatar", "avatar_content_type"])
    if previous:
        user.avatar.storage.delete(previous)
    return user


def delete_user_avatar(user: HumanUser) -> HumanUser:
    previous = user.avatar.name
    if not previous:
        return user
    user.avatar = ""
    user.avatar_content_type = ""
    user.save(update_fields=["avatar", "avatar_content_type"])
    user.avatar.storage.delete(previous)
    return user
