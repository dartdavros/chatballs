"""Общие помощники загрузчиков демо-сида.

Время в манифестах относительное (``minutesAgo`` / ``hoursAgo`` / ``daysAgo``):
демо должно выглядеть живым в момент установки («ждёт 6 мин», «вчера»).
Поля ``auto_now_add`` нельзя задать при создании — их откатывают точечным
``UPDATE`` после сохранения.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

# Детерминированный генератор: повторная установка даёт те же «случайные» ряды.
DEMO_SEED = 20260905


def rng() -> random.Random:
    return random.Random(DEMO_SEED)


def moment(item: dict, now: datetime, prefix: str = "") -> datetime | None:
    """Момент из ключей ``<prefix>MinutesAgo`` / ``<prefix>HoursAgo`` / ``<prefix>DaysAgo``.

    Без префикса ключи — ``minutesAgo``, ``hoursAgo``, ``daysAgo``. Возвращает
    ``None``, если ни одного ключа нет.
    """

    def key(name: str) -> str:
        return f"{prefix}{name[0].upper()}{name[1:]}" if prefix else name

    delta = timedelta()
    found = False
    for name, unit in (("minutesAgo", "minutes"), ("hoursAgo", "hours"), ("daysAgo", "days")):
        value = item.get(key(name))
        if value is not None:
            delta += timedelta(**{unit: float(value)})
            found = True
    return now - delta if found else None


def backdate(instance: models.Model, when: datetime | None, *fields: str) -> None:
    """Переписывает временные поля записи (created_at и т. п.) без сигналов."""
    if when is None:
        return
    names = fields or ("created_at",)
    values = {name: when for name in names if _has_field(instance, name)}
    if not values:
        return
    type(instance)._base_manager.filter(pk=instance.pk).update(**values)
    for name, value in values.items():
        setattr(instance, name, value)


def _has_field(instance: models.Model, name: str) -> bool:
    try:
        instance._meta.get_field(name)
    except Exception:  # noqa: BLE001
        return False
    return True


def now() -> datetime:
    return timezone.now()
