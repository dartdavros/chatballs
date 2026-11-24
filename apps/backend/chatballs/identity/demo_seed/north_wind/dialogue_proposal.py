"""Collect the school's brief and price it against the local wholesale stock."""

import re

from chatballs.identity.demo_seed.north_wind.commands import ProposalInput
from chatballs.identity.demo_seed.north_wind.dialogue_input import (
    Reply,
    confirmation,
    localized,
    products_in,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write
from chatballs.identity.demo_seed.north_wind.wholesale import (
    MODELS,
    party_options,
    prepare_party_quote,
)

_CITY = {"казан": "kazan", "kazan": "kazan", "иннополис": "innopolis", "innopolis": "innopolis",
         "челн": "chelny", "chelny": "chelny"}
_DETAILS = {"компания": "company", "company": "company", "контакт": "contact", "contact": "contact",
            "адрес": "address", "address": "address", "почта": "email", "email": "email"}


def proposal_reply(dataset, context, draft, text, language, message_id):
    tr = lambda ru, en: localized(language, ru, en)  # noqa: E731
    search, model = _read_brief(draft, text)
    if not {"quantities", "city", "budget"} <= search.keys():
        return Reply(tr("Укажите количество по размерам, город доставки и бюджет за комплект. Например: M 6, L 10, XL 4, Казань, бюджет 35000.",
                        "Give the quantities by size, delivery city and budget per suit. For example: M 6, L 10, XL 4, Kazan, budget 35000."))
    state = dataset.shop_state
    try:
        options = party_options(state, **search)
    except ShopError:
        return Reply(tr("Проверьте количество по размерам. Общий заказ может содержать до 100 комплектов.",
                        "Check the quantities by size. A single order may contain up to 100 suits."))
    if not model or not any(item["id"] == model and item["available"] and item["withinBudget"] for item in options["options"]):
        return _choices(options, language)
    if not draft.get("quote"):
        draft["quote"] = execute_write(context, dataset.generation, prepare_party_quote,
            key=f"chat-quote:{message_id}", command={"product_id": model, **search})
    quote = draft["quote"]
    summary = _calculation(quote, language)
    details = draft.setdefault("details", {})
    for line in text.splitlines():
        name, separator, value = line.partition(":")
        if separator and name.strip().casefold() in _DETAILS:
            details[_DETAILS[name.strip().casefold()]] = value.strip()
    if set(details) != set(_DETAILS.values()):
        return Reply(summary + "\n" + tr("Пришлите отдельными строками поля «Компания:», «Контакт:», «Адрес:» и «Почта:».",
                                          "Send these fields on separate lines: Company:, Contact:, Address:, Email:."))
    serializer = ProposalInput(data={"quote_id": quote["id"], **details, "confirmed": True})
    if not serializer.is_valid():
        return Reply(summary + "\n" + tr("Проверьте реквизиты компании и рабочую почту.",
                                         "Check the company details and work email."))
    details_display = tr("Компания, контакт, адрес и почта:", "Company, contact, address and email:")
    review = "\n".join((summary, details_display, *(details[key] for key in ("company", "contact", "address", "email"))))
    return Reply(review + "\n" + confirmation(draft, message_id, dict(serializer.validated_data), language))


def _read_brief(draft, text):
    start = dict(draft.get("search", {}))
    search = start.copy()
    lowered = text.casefold()
    brief = " ".join(line for line in lowered.splitlines() if line.partition(":")[0].strip() not in _DETAILS)
    sizes = {size.upper(): int(count) for size, count in re.findall(r"\b(m|xl|l)\s*[=:×-]?\s*(\d{1,3})\b", brief)}
    if sizes:
        search["quantities"] = sizes
    city = next((key for label, key in _CITY.items() if label in brief), None)
    if city:
        search["city"] = city
    budget = re.search(r"(?:бюджет|budget)\s*[:=]?\s*(\d[\d \u202f]{0,8})", brief)
    if budget:
        search["budget"] = int("".join(budget[1].split()))
    model = next((key for key in products_in(brief) if key in MODELS), draft.get("model"))
    if search != start or model != draft.get("model"):
        draft.pop("quote", None)
    draft.update(search=search, model=model)
    return search, model


def _choices(options, language):
    tr = lambda ru, en: localized(language, ru, en)  # noqa: E731
    rows = []
    cards = []
    for item in options["options"]:
        stock = ", ".join(f"{key} {value}" for key, value in item["stock"].items())
        limits = []
        if not item["available"]:
            limits.append(tr("не хватает на всю партию", "not enough for the whole batch"))
        if not item["withinBudget"]:
            limits.append(tr("выше бюджета", "over budget"))
        specs = tr(f"утепление {item['insulation']} г/м², мембрана {item['membrane']} мм",
                   f"insulation {item['insulation']} g/m², membrane {item['membrane']} mm")
        rows.append(f"{item['name']} · {item['basePrice']} ₽ · {specs} · {stock}" + (" · " + ", ".join(limits) if limits else ""))
        cards.append({**{key: item[key] for key in ("id", "name", "basePrice", "insulation", "membrane")},
                      "stock": stock, "availability": ", ".join(limits), "available": not limits})
    heading = tr("Подборка для горнолыжной школы", "Ski school selection")
    followup = tr("Выберите модель с доступным остатком и ценой в пределах бюджета.",
                  "Choose a model with enough stock and a price within your budget.")
    return Reply("\n".join((heading, *rows, followup)), recommendations={
        "language": language, "heading": heading, "followup": followup, "products": cards,
    })


def _calculation(quote, language):
    return localized(language,
        f"{quote['productName']} · {quote['quantity']} комплектов. Цена за комплект {quote['unitPrice']} ₽, скидка {quote['discountPercent']}%. "
        f"Партия {quote['subtotal']} ₽, доставка {quote['delivery']} ₽ за {quote['days']} дн. Итого {quote['total']} ₽. Расчёт действует до {quote['validUntil'][:16]} UTC.",
        f"{quote['productName']} · {quote['quantity']} suits. Unit price RUB {quote['unitPrice']}, discount {quote['discountPercent']}%. "
        f"Batch RUB {quote['subtotal']}, delivery RUB {quote['delivery']} in {quote['days']} days. Total RUB {quote['total']}. Quote valid until {quote['validUntil'][:16]} UTC.")
