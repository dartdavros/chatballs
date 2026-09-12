"""Язык интерфейса: выбор языка запроса и каталог сообщений."""

from chatballs.i18n.audience import customer_language
from chatballs.i18n.catalog import current_language, t, tn
from chatballs.i18n.languages import (
    DEFAULT_LANGUAGE,
    ENGLISH,
    INHERIT,
    LANGUAGE_CODES,
    LANGUAGES,
    RUSSIAN,
    first_chosen,
    normalize_language,
    parse_accept_language,
    resolve_language,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "ENGLISH",
    "INHERIT",
    "LANGUAGES",
    "LANGUAGE_CODES",
    "RUSSIAN",
    "current_language",
    "customer_language",
    "first_chosen",
    "normalize_language",
    "parse_accept_language",
    "resolve_language",
    "t",
    "tn",
]
