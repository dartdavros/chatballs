"""Input primitives for the local shop's conversational flows."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from secrets import token_hex

from django.utils import timezone

from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS


@dataclass(frozen=True)
class Reply:
    text: str
    handoff: bool = False
    document: dict | None = None
    recommendations: dict | None = None


def products_in(text):
    return [key for key, product in PRODUCTS.items() if product["name"].casefold() in text or key in text.split()]


def pickup_in(text):
    if re.search(r"горк|gorki", text):
        return "gorki"
    if re.search(r"центр|cent(?:re|er)", text):
        return "center"
    return None


def day_in(text, now=None):
    today = (now or timezone.now()).astimezone(MOSCOW).date()
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if match:
        return date.fromisoformat(match[0])
    if re.search(r"завтра|tomorrow", text):
        return today + timedelta(days=1)
    if re.search(r"сегодня|today", text):
        return today
    return None


def time_in(text):
    match = re.search(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", text)
    return match[0].zfill(5) if match else None


def localized(language, ru, en):
    return ru if language == "ru" else en


def confirmation(draft, message_id, command, language):
    code = token_hex(3)
    draft["confirmation"] = {"code": code, "messageId": message_id, "command": command}
    return localized(language, f"Для подтверждения отправьте «Подтверждаю {code}».", f"To confirm, send ‘Confirm {code}’.")


def confirmation_requested(text):
    return bool(re.match(r"^(?:подтверждаю|confirm)(?:\s|$)", text))


def confirmed(text, pending, message_id):
    return bool(pending and message_id > pending["messageId"] and re.fullmatch(
        r"(?:подтверждаю|confirm)\s+" + re.escape(pending["code"]) + r"[.!]?", text,
    ))
