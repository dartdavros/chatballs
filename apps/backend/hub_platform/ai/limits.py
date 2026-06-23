from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from hub_platform.ai.models import LlmInvocation, LlmInvocationStatus


class LimitExceeded(Exception):
    pass


def _day_start():
    now = timezone.localtime()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def daily_cost_micros(product=None) -> int:
    queryset = LlmInvocation.objects.filter(created_at__gte=_day_start(), status=LlmInvocationStatus.SUCCESS)
    if product is not None:
        queryset = queryset.filter(product=product)
    return queryset.aggregate(total=Sum("cost_micros"))["total"] or 0


def assert_within_limits(product, agent) -> None:
    global_limit = settings.HUB_AI_GLOBAL_DAILY_COST_LIMIT_MICROS
    if global_limit and daily_cost_micros() >= global_limit:
        raise LimitExceeded("Global daily AI cost limit reached")
    product_limit = (agent.limits or {}).get("dailyCostMicros")
    if product_limit and daily_cost_micros(product) >= product_limit:
        raise LimitExceeded("Product daily AI cost limit reached")
