from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus


class LimitExceeded(Exception):
    pass


def _day_start():
    now = timezone.localtime()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def daily_cost_micros(channel=None) -> int:
    queryset = LlmInvocation.objects.filter(created_at__gte=_day_start(), status=LlmInvocationStatus.SUCCESS)
    if channel is not None:
        queryset = queryset.filter(channel=channel)
    return queryset.aggregate(total=Sum("cost_micros"))["total"] or 0


def assert_within_limits(channel, agent) -> None:
    global_limit = settings.HUB_AI_GLOBAL_DAILY_COST_LIMIT_MICROS
    if global_limit and daily_cost_micros() >= global_limit:
        raise LimitExceeded("Global daily AI cost limit reached")
    channel_limit = (agent.limits or {}).get("dailyCostMicros")
    if channel_limit and daily_cost_micros(channel) >= channel_limit:
        raise LimitExceeded("Channel daily AI cost limit reached")
