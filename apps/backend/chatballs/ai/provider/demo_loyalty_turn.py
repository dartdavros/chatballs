"""Explain the signed shopper's current benefits from the real local tool."""

import re

from chatballs.ai.provider.demo import HANDOFF_TOKEN
from chatballs.ai.provider.demo_shop_turn import _call, _turn_results
from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS
from chatballs.identity.demo_seed.north_wind.loyalty_site import LOYALTY_TASK, LOYALTY_TOOL
from chatballs.webchat.proactive_plan import FIRST_REPLY_TASK


def plan_loyalty_turn(messages, tools):
    if not any(tool.name == LOYALTY_TOOL for tool in tools):
        return None
    for index in reversed(range(len(messages))):
        message = messages[index]
        if message.role == "user":
            if not re.search(r"бонус|списа|reward|points|loyalty|redeem", message.content, re.I):
                return None
            return _answer(messages[index + 1:], _requested_product(message.content))
        if message.role == "system" and message.content == FIRST_REPLY_TASK + LOYALTY_TASK:
            return _answer(messages[index + 1:], "alpine")
    return None


def _requested_product(text):
    return next((key for key, product in PRODUCTS.items() if product["name"].casefold() in text.casefold()), "alpine")


def _answer(messages, product):
    results = _turn_results(messages)
    if LOYALTY_TOOL not in results:
        return "", (_call(LOYALTY_TOOL, {"product_id": product}),)
    result = results[LOYALTY_TOOL]
    language = result.get("language", "ru")
    if result.get("product") != product or type(result.get("balance")) is not int:
        return f'{t("ai.demo_handover", language=language)}\n{HANDOFF_TOKEN}', ()
    balance = t("ai.demo_loyalty_balance", language=language, balance=result["balance"])
    terms = t("ai.demo_loyalty_terms" if result.get("allowed") is True else "ai.demo_loyalty_excluded",
              language=language, maximum=result.get("maxBonus", 0))
    return f"{balance} {terms}", ()
