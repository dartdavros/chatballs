"""A chat and the storefront quote and book against one fitting calendar."""

import re
from datetime import date, datetime, timedelta

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.appointments import FITTING_DURATION, fitting_slots
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, STORES, pickup_point
from chatballs.identity.demo_seed.north_wind.dialogue_input import (
    Reply,
    confirmation,
    day_in,
    localized,
    pickup_in,
    products_in,
    time_in,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError


def fitting_reply(state, draft, text, language, message_id):
    tr = lambda ru, en: localized(language, ru, en)  # noqa: E731
    conditions = (draft.get("products"), draft.get("day"), draft.get("store"))
    models = products_in(text)
    if models:
        draft["products"] = models
    try:
        day = day_in(text)
    except ValueError:
        return Reply(tr("Укажите дату в формате ГГГГ-ММ-ДД.", "Enter a date in YYYY-MM-DD format."))
    if day:
        draft["day"] = day.isoformat()
    store = pickup_in(text)
    if store:
        draft["store"] = store
    if conditions != (draft.get("products"), draft.get("day"), draft.get("store")):
        draft.pop("time", None)
    if phone := re.search(r"(?:телефон|phone)\s*[:=]?\s*(\+?\d[\d ()-]{8,21}\d)", text):
        digits = re.sub(r"\D", "", phone[1])
        if not 10 <= len(digits) <= 15:
            return Reply(tr("Проверьте номер телефона для записи.", "Check the phone number for the booking."))
        draft["phone"] = f"+{digits}"
    if len(draft.get("products", [])) != 2 or not draft.get("day"):
        return Reply(tr("Назовите две разные модели и дату примерки, например «Alpine Pro и Ridge Motion завтра».",
                        "Name two different models and a date, for example ‘Alpine Pro and Ridge Motion tomorrow’."))
    day = date.fromisoformat(draft["day"])
    try:
        slots = {point: fitting_slots(state, store=point, day=day) for point in STORES}
    except ShopError:
        return Reply(tr("Выберите дату от сегодня до недели вперёд.", "Choose a date from today through the next seven days."))
    if time := time_in(text):
        draft["time"] = time
    selected_time = draft.get("time")
    chosen = draft.get("store")
    if selected_time and chosen:
        selected = next((slot for slot in slots[chosen] if slot[11:16] == selected_time), None)
        if selected:
            if "phone" not in draft:
                return Reply(tr("Укажите телефон для связи, например «Телефон: +7 000 000 00 01».",
                                "Enter a contact phone, for example ‘Phone: +7 000 000 00 01’."))
            now = timezone.now()
            expires = min(datetime.fromisoformat(selected), now + timedelta(minutes=20))
            command = {"store": chosen, "starts_at": selected, "products": draft["products"],
                       "validUntil": expires.isoformat(), "contact_phone": draft["phone"]}
            point = pickup_point(state, chosen)
            labels = ", ".join(PRODUCTS[key]["name"] for key in draft["products"])
            summary = tr(
                f"Примерка с консультантом, {labels}. {day:%d.%m.%Y} в {selected_time} МСК, {point['address']}. Бесплатно, 45 минут. Запись на имя Ольги Мироновой, {draft['phone']}. Условия действуют до {expires.astimezone(datetime.fromisoformat(selected).tzinfo):%H:%M} МСК.",
                f"Fitting with a consultant, {labels}. {day:%d %b %Y} at {selected_time} Moscow time, {point['address']}. Free, 45 minutes. The booking is for Olga Mironova, {draft['phone']}. Terms are valid until {expires.astimezone(datetime.fromisoformat(selected).tzinfo):%H:%M} Moscow time.",
            )
            return Reply(summary + "\n" + confirmation(draft, message_id, command, language))
    minutes = int(FITTING_DURATION.total_seconds() / 60)
    none = tr("свободных интервалов нет", "no available times")
    lines = [f"{pickup_point(state, point)['name']} · {', '.join(slot[11:16] for slot in times[:5]) or none}"
             for point, times in slots.items()]
    heading = tr(f"{day:%d.%m.%Y}, московское время. Примерка бесплатная, {minutes} минут.",
                 f"{day:%d %b %Y}, Moscow time. The fitting is free and lasts {minutes} minutes.")
    prompt = tr("Назовите магазин и время.", "Tell me the store and time.")
    if selected_time and chosen:
        draft.pop("time", None)
        prompt = tr("Этот интервал занят или недоступен. Выберите другой интервал или магазин.",
                    "That time is booked or unavailable. Choose another time or store.")
    return Reply("\n".join((heading, *lines, prompt)))
