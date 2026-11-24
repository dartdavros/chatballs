"""The offline shop assistant reads the actual catalogue before it answers."""

import re

from chatballs.ai.provider.demo import HANDOFF_TOKEN, _language_of
from chatballs.ai.provider.demo_shop_turn import HTTP_STATUS, _call, _turn_results
from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, available_choices

SEARCH = "search_products"
PRODUCT = "get_product"
_BUDGET = re.compile(r"(\d{2,3}[\s,]?\d{3})\s*(?:₽|руб|rub)", re.I)
_SIZE = re.compile(r"\b(M|L|XL)\b", re.I)
_CATALOG = re.compile(r"костюм|пример|самовывоз|наличи|ski suit|pick.?up|stock|fitting", re.I)


def plan_catalog_turn(messages, tools):
    if not {SEARCH, PRODUCT, HTTP_STATUS}.issubset({tool.name for tool in tools}):
        return None
    question_index = next((index for index in reversed(range(len(messages)))
                           if messages[index].role == "user"), None)
    if question_index is None:
        return None
    question = messages[question_index].content
    product = next(
        (key for key, item in PRODUCTS.items() if item["name"].casefold() in question.casefold()),
        None,
    )
    if not product and not _CATALOG.search(question):
        return None
    language = _language_of(question)
    size = _SIZE.search(question)
    arguments = {"size": size.group().upper() if size else "L"}
    tool = PRODUCT if product else SEARCH
    if product:
        arguments["product_id"] = product
    else:
        limit = _BUDGET.search(question)
        if limit:
            arguments["budget"] = int(re.sub(r"\D", "", limit.group(1)))
    return _answer(messages[question_index + 1:], tool, arguments, language)


def _answer(messages, tool, arguments, language):
    results = _turn_results(messages)
    if tool not in results:
        return "", (_call(tool, arguments),)
    result = results[tool]
    if "error" in result or (tool == PRODUCT and "name" not in result):
        return f'{t("ai.demo_handover", language=language)}\n{HANDOFF_TOKEN}', ()
    if tool == PRODUCT:
        return _product_reply(result, size=arguments["size"], language=language), ()
    return _search_reply(result.get("products", []), size=arguments["size"], language=language), ()


def _specification(product, language):
    return t(
        "ai.demo_catalog_product", language=language, name=product["name"], price=product["basePrice"],
        insulation=product["insulation"], membrane=product["membrane"],
    )


def _product_reply(product, *, size, language):
    specification = _specification(product, language)
    stock = ", ".join(f'{point["name"]} — {point["available"]}' for point in product["availability"])
    return f'{specification}\n{t("ai.demo_catalog_availability", language=language, size=size, stock=stock)}'


def _search_reply(products, *, size, language):
    choices = available_choices(products)
    if not choices:
        return t("ai.demo_catalog_empty", language=language, size=size)
    intro = t("ai.demo_catalog_selection", language=language, size=size)
    rows = [f'• {_specification(item, language)}' for item in choices]
    return "\n".join((intro, *rows, t("ai.demo_catalog_followup", language=language)))
