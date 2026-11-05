"""Pure timezone slot calculation with explicit fold, gap and misfire policies."""

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NEVER = datetime.max.replace(tzinfo=UTC)


def matches(trigger, day):
    if trigger.get("date"):
        return day == date.fromisoformat(trigger["date"])
    frequency = trigger.get("frequency", "days")
    if frequency == "monthly":
        number = trigger["dayOfMonth"]
        return day.day == (monthrange(day.year, day.month)[1] if number == "last" else number)
    return frequency == "daily" or (day.weekday() < 5 if frequency == "weekdays" else day.weekday() in trigger["days"])


def on_day(trigger, day):
    zone = ZoneInfo(trigger["timezone"])
    local = datetime.combine(day, time.fromisoformat(trigger["time"]))
    for _ in range(1441):
        candidates = sorted({local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            for fold in (0, 1) if local.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone).replace(tzinfo=None) == local})
        if candidates:
            return candidates[-1] if trigger["ambiguous"] == "second" else candidates[0]
        if trigger["nonexistent"] == "skip":
            return None
        local = local.replace(second=0, microsecond=0) + timedelta(minutes=1)
    raise ValueError("schedule gap exceeds one day")


def next_slot(trigger, after):
    day = date.fromisoformat(trigger["date"]) if trigger.get("date") else after.astimezone(ZoneInfo(trigger["timezone"])).date()
    for _ in range(370):
        if matches(trigger, day):
            slot = on_day(trigger, day)
            if slot is not None and slot > after:
                return slot
        if trigger.get("date"):
            break
        day += timedelta(days=1)
    return NEVER


def latest_slot(trigger, after, now):
    day = date.fromisoformat(trigger["date"]) if trigger.get("date") else now.astimezone(ZoneInfo(trigger["timezone"])).date()
    for _ in range(370):
        if matches(trigger, day):
            slot = on_day(trigger, day)
            if slot is not None and after < slot <= now:
                return slot
            if slot is not None and slot <= after:
                return None
        if trigger.get("date"):
            break
        day -= timedelta(days=1)
    return None
