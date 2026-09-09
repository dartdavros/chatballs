"""Языки интерфейса и правило, по которому запрос выбирает свой.

Язык не выводится из окружения и не задаётся переменной: его выбирает человек.
Владелец задаёт язык организации — на нём рабочее место открывается всем, кто
в неё вошёл; отдельный сотрудник может переопределить его в профиле, и тогда
организация ему не указ. До входа организации ещё нет, и язык берётся из
настроек установки: на нём показываются логин, сброс пароля и мастер первого
запуска.
"""

from __future__ import annotations

from typing import Final

RUSSIAN: Final = "ru"
ENGLISH: Final = "en"

# Порядок важен: первый язык — тот, на котором написан исходный каталог и на
# который приходится фолбэк, когда перевода нет.
LANGUAGES: Final[tuple[tuple[str, str], ...]] = (
    (RUSSIAN, "Русский"),
    (ENGLISH, "English"),
)

LANGUAGE_CODES: Final[tuple[str, ...]] = tuple(code for code, _ in LANGUAGES)
DEFAULT_LANGUAGE: Final = RUSSIAN

# Пустая строка в профиле сотрудника означает «как в организации», а в
# организации — «как в установке». Это не язык, а отсутствие выбора, поэтому
# отдельного значения в LANGUAGES у неё нет.
INHERIT: Final = ""


def normalize_language(value: object) -> str:
    """Привести код к поддерживаемому языку или вернуть INHERIT.

    Принимает и «ru-RU», и «RU», и «ru_ru»: браузер, операционная система и
    заголовок Accept-Language пишут регион по-разному, а выбор один и тот же.
    Неизвестный язык — не ошибка: это просьба, которую нечем удовлетворить, и
    она сводится к «как выше по цепочке».
    """

    if not isinstance(value, str):
        return INHERIT
    code = value.strip().replace("_", "-").lower()
    if not code:
        return INHERIT
    base = code.partition("-")[0]
    return base if base in LANGUAGE_CODES else INHERIT


def parse_accept_language(header: str | None) -> str:
    """Первый поддерживаемый язык из Accept-Language, иначе INHERIT.

    Заголовок разбирается по убыванию q-веса: «en;q=0.9, ru» означает русский,
    хотя английский стоит первым.
    """

    if not header:
        return INHERIT
    weighted: list[tuple[float, int, str]] = []
    for position, part in enumerate(header.split(",")):
        token, _, params = part.strip().partition(";")
        code = normalize_language(token)
        if not code:
            continue
        quality = 1.0
        for param in params.split(";"):
            key, _, raw = param.strip().partition("=")
            if key.strip() == "q":
                try:
                    quality = float(raw)
                except ValueError:
                    quality = 0.0
        weighted.append((-quality, position, code))
    if not weighted:
        return INHERIT
    weighted.sort()
    return weighted[0][2]


def first_chosen(*candidates: str) -> str:
    """Первый уровень цепочки, который язык действительно выбрал.

    Возвращает INHERIT, если не выбрал ни один: вызывающий по этому признаку
    решает, спрашивать ли следующий уровень. Нужно там, где следующий уровень
    стоит запроса к базе, — незачем его читать, если выбор уже сделан.
    """

    for candidate in candidates:
        code = normalize_language(candidate)
        if code:
            return code
    return INHERIT


def resolve_language(
    *,
    user_language: str = INHERIT,
    organization_language: str = INHERIT,
    instance_language: str = INHERIT,
    accept_language: str | None = None,
) -> str:
    """Язык одного запроса: от личного выбора к общему умолчанию.

    Порядок фиксированный — профиль, организация, установка, браузер. Браузер
    стоит последним и работает только до входа: после входа язык человека уже
    известен, и подстраиваться под ноутбук, с которого он сегодня зашёл, не
    нужно.
    """

    chosen = first_chosen(user_language, organization_language, instance_language)
    return chosen or parse_accept_language(accept_language) or DEFAULT_LANGUAGE
