"""Каталог сообщений и перевод строки под язык запроса.

Переводы лежат обычными питоновскими словарями, а не в .po: продукт ставят
одной командой из готового образа, и лишний бинарный шаг сборки (msgfmt) в этой
цепочке нечем оправдать. Django и DRF свои строки при этом продолжают
переводить штатно — язык запроса активируется через ``translation.activate``,
и их скомпилированные каталоги подхватываются как обычно.

Русский каталог — источник истины: ключ появляется сначала в нём. Английский
обязан повторять его набор ключей один в один, это проверяется тестом, а не
глазами. Пропущенный перевод не роняет запрос: строка выходит по-русски, и это
видно, тогда как исключение в середине ответа не видно никому.
"""

from __future__ import annotations

from typing import Final

from django.utils.translation import get_language

from chatballs.i18n.languages import DEFAULT_LANGUAGE, normalize_language
from chatballs.i18n.messages import CATALOG

# Форма множественного числа по правилам CLDR. Русскому нужны четыре («1 диалог»,
# «2 диалога», «5 диалогов», «1,5 диалога»), английскому — две, и код, который
# просто клеит «s», на русском не работает ни в одной строке.
PluralForms = dict[str, str]
Message = str | PluralForms

_OTHER: Final = "other"


def _plural_category(language: str, count: int | float) -> str:
    if language == "ru":
        if count != int(count):
            return _OTHER
        i = abs(int(count))
        if i % 10 == 1 and i % 100 != 11:
            return "one"
        if i % 10 in (2, 3, 4) and i % 100 not in (12, 13, 14):
            return "few"
        return "many"
    # Английский и всё, что добавят следом с двумя формами.
    if count == 1 and count == int(count):
        return "one"
    return _OTHER


def _lookup(key: str, language: str) -> Message | None:
    table = CATALOG.get(language)
    if table is not None and key in table:
        return table[key]
    if language != DEFAULT_LANGUAGE:
        fallback = CATALOG.get(DEFAULT_LANGUAGE)
        if fallback is not None and key in fallback:
            return fallback[key]
    return None


def current_language() -> str:
    """Язык, активированный для этого запроса (или язык по умолчанию)."""

    return normalize_language(get_language()) or DEFAULT_LANGUAGE


def t(key: str, /, language: str | None = None, **params: object) -> str:
    """Строка каталога на языке запроса, с подстановкой ``{имя}``.

    Неизвестный ключ возвращается как есть. Это заметно в интерфейсе, но не
    ломает ответ: опечатка в ключе не должна превращать сохранение настроек в
    пятисотую.
    """

    code = normalize_language(language) or current_language()
    message = _lookup(key, code)
    if message is None:
        return key
    if isinstance(message, dict):
        message = message.get(_OTHER, key)
    return message.format(**params) if params else message


def tn(key: str, count: int | float, /, language: str | None = None, **params: object) -> str:
    """Строка с числом: форма выбирается по правилам языка.

    ``count`` подставляется в ``{count}`` без отдельного указания, потому что
    строка с числом без самого числа не нужна ни разу.
    """

    code = normalize_language(language) or current_language()
    message = _lookup(key, code)
    if message is None:
        return key
    if isinstance(message, dict):
        category = _plural_category(code, count)
        message = message.get(category) or message.get(_OTHER) or key
    return message.format(count=count, **params)
