"""Resolve local clock once, including DST, rather than sleeping a worker."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenarios.values import resolve_value


def due_at(block, values, registry=None):
    now = timezone.now()
    mode = block["mode"]
    if mode == "duration":
        return now + timedelta(seconds=block["duration"])
    if mode == "until":
        result = parse_datetime(resolve_value(block["until"], values, registry))
        if result is None or timezone.is_naive(result):
            raise ExecutionDenied("arguments")
        return result
    if mode != "clock":
        return now + timedelta(seconds=block.get("timeout", 86400))
    if block["day"] == "work":
        # This domain has no working calendar yet. A weekday is not evidence.
        raise ExecutionDenied("calendar_unavailable")
    zone = ZoneInfo(block["timezone"])
    local = now.astimezone(zone)
    day = datetime.fromisoformat(block["date"]).date() if block["day"] == "date" else local.date()
    clock = time.fromisoformat(block["time"])
    for _ in range(3):
        naive = datetime.combine(day, clock)
        for minute in range(181):
            candidate = naive + timedelta(minutes=minute)
            instants = sorted({candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC) for fold in (0, 1)
                if candidate.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone).replace(tzinfo=None) == candidate})
            future = [instant for instant in instants if instant > now]
            if future:
                return future[0]
            if instants:
                break
        if block["day"] == "date":
            return now
        day += timedelta(days=1)
    raise ExecutionDenied("arguments")
