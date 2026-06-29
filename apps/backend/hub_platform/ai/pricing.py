from django.conf import settings

# micro-USD за токен (1 USD = 1_000_000 micro); значение = цена в USD за 1M токенов.
# Fallback на случай, если провайдер не вернул фактическую стоимость (usage.cost).
# Реальные/уточнённые цены задаются через HUB_AI_PRICING.
DEFAULT_PRICING = {
    "openai/gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "anthropic/claude-sonnet-4.6": {"prompt": 3.0, "completion": 15.0},
}


def cost_micros(model: str, prompt_tokens: int, completion_tokens: int) -> int:
    table = {**DEFAULT_PRICING, **getattr(settings, "HUB_AI_PRICING", {})}
    price = table.get(model)
    if not price:
        return 0
    return round(prompt_tokens * price["prompt"] + completion_tokens * price["completion"])
