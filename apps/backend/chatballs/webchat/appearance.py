"""Оформление веб-виджета: ``integration.config.appearance`` (SPEC-0021 R-1).

Иконки: пустая строка — стандартный знак агента; у шапки пустая строка —
«как у кнопки», ``None`` — без иконки.
"""

import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.webchat.custom_css import sanitize_custom_css
from chatballs.webchat.launcher_css import launcher_css

DEFAULT_ACCENT = "#1677ff"
POSITIONS = ("left", "right")
SIZES = (48, 56, 64)
SHAPES = ("circle", "rounded", "square")
MAX_CUSTOM_CSS_BYTES = 10 * 1024
MAX_ICON_URL_LENGTH = 2048

DEFAULTS = {
    "accent": "",
    "theme": "light",
    "launcherIcon": "",
    "headerIcon": "",
    "launcherPosition": "right",
    "launcherSize": 56,
    "launcherShape": "circle",
    "customCss": "",
}

_HEX = re.compile(r"#[0-9a-f]{6}")
_URL_NOISE = re.compile(r"[\x00-\x20\x7f\\]")


def _invalid(key: str) -> ValidationError:
    return ValidationError({"config": t(key)})


def _accent(value: object) -> str:
    accent = str(value or "").strip().lower()
    if accent and not _HEX.fullmatch(accent):
        raise _invalid("settings.appearance_accent")
    return accent


def _choice(value: object, allowed: tuple, error: str) -> object:
    if isinstance(value, bool) or value not in allowed:
        raise _invalid(error)
    return allowed[allowed.index(value)]


def _icon(value: object, *, nullable: bool) -> str | None:
    if value is None:
        return None if nullable else ""
    if not isinstance(value, str):
        raise _invalid("settings.appearance_icon")
    url = value.strip()
    if not url:
        return ""
    parsed = urlsplit(url)
    public = parsed.scheme in ("http", "https") and bool(parsed.netloc)
    # Путь от корня — файл в хранилище на этом же сервере; «//host» — уже чужой адрес.
    local = not parsed.scheme and url.startswith("/") and not url.startswith("//")
    if len(url) > MAX_ICON_URL_LENGTH or _URL_NOISE.search(url) or not (public or local):
        raise _invalid("settings.appearance_icon")
    return url


def _custom_css(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _invalid("settings.appearance")
    if len(value.encode("utf-8")) > MAX_CUSTOM_CSS_BYTES:
        raise _invalid("settings.appearance_css_too_large")
    return sanitize_custom_css(value).strip()


def stored_appearance(config: dict | None) -> dict:
    """Сохранённое оформление с умолчаниями; цвет — и из прежнего ``config.accent``."""
    config = config if isinstance(config, dict) else {}
    stored = config.get("appearance")
    appearance = {**DEFAULTS, **(stored if isinstance(stored, dict) else {})}
    appearance["accent"] = appearance["accent"] or str(config.get("accent") or "")
    return appearance


def normalize_appearance(config: dict, previous: dict | None = None) -> dict:
    """Оформление из ``config`` запроса.

    Форма подключения отправляет config целиком, но без ``appearance`` —
    тогда оформление остаётся прежним, меняется только цвет из ``config.accent``.
    """
    raw = config.get("appearance")
    if raw is None:
        appearance = stored_appearance(previous)
        if "accent" in config:
            appearance["accent"] = _accent(config["accent"])
        return appearance
    if not isinstance(raw, dict):
        raise _invalid("settings.appearance")
    return {
        "accent": _accent(raw["accent"] if "accent" in raw else config.get("accent")),
        "theme": _choice(raw.get("theme", stored_appearance(previous)["theme"]),
                         ("light", "dark"), "settings.appearance_theme"),
        "launcherIcon": _icon(raw.get("launcherIcon"), nullable=False),
        "headerIcon": _icon(raw.get("headerIcon", ""), nullable=True),
        "launcherPosition": _choice(
            raw.get("launcherPosition", DEFAULTS["launcherPosition"]),
            POSITIONS,
            "settings.appearance_position",
        ),
        "launcherSize": _choice(
            raw.get("launcherSize", DEFAULTS["launcherSize"]),
            SIZES,
            "settings.appearance_size",
        ),
        "launcherShape": _choice(
            raw.get("launcherShape", DEFAULTS["launcherShape"]),
            SHAPES,
            "settings.appearance_shape",
        ),
        "customCss": _custom_css(raw.get("customCss")),
    }


def appearance_payload(config: dict) -> dict:
    appearance = stored_appearance(config)
    appearance.pop("launcherCss", None)
    styles = launcher_css(appearance["customCss"])
    if styles:
        appearance["launcherCss"] = styles
    return appearance


def public_appearance(presentation: dict) -> dict:
    """Оформление для виджета: умолчания подставлены, иконка шапки разрешена."""
    appearance = appearance_payload(presentation)
    appearance["accent"] = appearance["accent"] or DEFAULT_ACCENT
    if appearance["headerIcon"] == "":
        appearance["headerIcon"] = appearance["launcherIcon"]
    return appearance
