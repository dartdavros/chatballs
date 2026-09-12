"""Визуальные темы порталов (SPEC-CHATBALLS-0028 §6, ADR-CHATBALLS-0044).

Бэкенд хранит только идентификатор темы, выбранную цветовую схему и
произвольные параметры темы. Каталог тем живёт в коде фронтенда
(`apps/internal-ui/src/features/help-center/themes/`) и здесь намеренно не
дублируется: неизвестный идентификатор деградирует до темы по умолчанию на
публичной странице, а не роняет API или БД.
"""

from __future__ import annotations

import json
import re

from django.core.exceptions import ValidationError
from django.db import models

from chatballs.i18n import t

DEFAULT_PORTAL_THEME = "classic"
PORTAL_THEME_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PORTAL_THEME_SETTINGS_MAX_BYTES = 4096


class PortalThemeScheme(models.TextChoices):
    LIGHT = "LIGHT", "Светлая"
    DARK = "DARK", "Тёмная"
    SYSTEM = "SYSTEM", "Как в системе"


def normalize_theme(value: str | None) -> str:
    theme = str(value or "").strip().lower()
    return theme or DEFAULT_PORTAL_THEME


def normalize_theme_scheme(value: str | None) -> str:
    scheme = str(value or "").strip().upper()
    return scheme or PortalThemeScheme.LIGHT


def validate_theme(value: str) -> None:
    if not PORTAL_THEME_ID_PATTERN.fullmatch(value or ""):
        raise ValidationError({"theme": t("portals.invalid_theme_id")})


def validate_theme_scheme(value: str) -> None:
    if value not in PortalThemeScheme.values:
        raise ValidationError({"themeScheme": t("portals.invalid_theme_scheme")})


def validate_theme_settings(value) -> dict:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValidationError({"themeSettings": t("portals.theme_settings_object")})
    for key in value:
        if not isinstance(key, str) or not PORTAL_THEME_ID_PATTERN.fullmatch(key):
            raise ValidationError({"themeSettings": t("portals.invalid_theme_setting_name")})
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as error:
        raise ValidationError(
            {"themeSettings": t("portals.theme_settings_json")}
        ) from error
    if len(encoded.encode("utf-8")) > PORTAL_THEME_SETTINGS_MAX_BYTES:
        raise ValidationError({"themeSettings": t("portals.theme_settings_too_large")})
    return value
