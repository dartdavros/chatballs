"""Сборка каталога: русский — источник истины, английский обязан его повторить.

Ключ пишется как «модуль.смысл» и не повторяет саму фразу: строку правят чаще,
чем переименовывают, и ключ вида «identity.email_taken» переживает
переформулировку, а «identity.email_already_used» — нет.
"""

from __future__ import annotations

from chatballs.i18n.messages import en, ru

CATALOG: dict[str, dict[str, object]] = {"ru": ru.MESSAGES, "en": en.MESSAGES}

__all__ = ["CATALOG"]
