"""Endpoint handling shared by Custom BYOK runtime and connectivity checks."""

from urllib.parse import urlsplit, urlunsplit

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-6.1-sol"


def normalize_base_url(base_url: str) -> str:
    """Accept an API root or a pasted generation endpoint, without duplicating paths."""
    parts = urlsplit(base_url.strip())
    path = parts.path.rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    return urlunsplit(parts._replace(path=path))


def responses_requested(base_url: str) -> bool:
    """A full /responses URL explicitly opts a compatible gateway into Responses."""
    return urlsplit(base_url.strip()).path.rstrip("/").endswith("/responses")


def is_gpt6(model: str) -> bool:
    return model == "gpt-6" or model.startswith(("gpt-6-", "gpt-6."))


def uses_responses(base_url: str, model: str) -> bool:
    # Do not change the wire protocol of arbitrary OpenAI-compatible servers,
    # OpenRouter, or older OpenAI models. GPT-6 tool calls need Responses.
    return responses_requested(base_url) or (
        urlsplit(base_url.strip()).hostname == "api.openai.com" and is_gpt6(model)
    )
