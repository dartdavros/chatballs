from django.conf import settings

# micro-USD за токен (1 USD = 1_000_000 micro). Иллюстративные значения;
# реальные цены задаются перед production через HUB_AI_PRICING.
DEFAULT_PRICING = {
    "openai/gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
}


def cost_micros(model: str, prompt_tokens: int, completion_tokens: int) -> int:
    table = {**DEFAULT_PRICING, **getattr(settings, "HUB_AI_PRICING", {})}
    price = table.get(model)
    if not price:
        return 0
    return round(prompt_tokens * price["prompt"] + completion_tokens * price["completion"])
