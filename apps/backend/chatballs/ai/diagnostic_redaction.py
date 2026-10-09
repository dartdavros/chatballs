"""Bounded diagnostic copies; credentials and personal values stay out of storage."""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.integrations.external_headers import stored_secret_headers

REDACTED = "[redacted]"
_SENSITIVE = re.compile(r"token|secret|password|authorization|cookie|api.?key|credential", re.I)
_URL = re.compile(r"https?://[^\s\"<>]+")
_TOKEN = re.compile(r"\[\[[^\[\]\n]{1,80}\]\]")
_ASSIGNMENT = re.compile(
    r"((?:[\w-]*(?:token|secret|password|api[_-]?key|authorization|cookie)[\w-]*)"
    r"\s*[=:]\s*[\"']?)([^\s\"'&,;<>]+)", re.I,
)
_BEARER = re.compile(r"\b(Bearer|Basic)\s+[^\s\"'<>]+", re.I)
_TOKEN_COUNTS = {"prompt_tokens", "completion_tokens", "total_tokens", "max_tokens", "max_completion_tokens"}


class DiagnosticRedactor:
    def __init__(self, pseudonymizer: Pseudonymizer, secrets=()) -> None:
        self.pseudonymizer = pseudonymizer
        values = {str(value) for value in secrets if value is not None and str(value)}
        # Encoded credentials can appear in URLs, JSON or exception messages.
        values |= {quote(value, safe="") for value in values}
        values |= {json.dumps(value, ensure_ascii=False)[1:-1] for value in values}
        self.secrets = sorted(values, key=len, reverse=True)
        self.remaining = 512 * 1024
        self.truncated = False

    def text(self, value: str, *, bounded: bool = True) -> str:
        for secret in self.secrets:
            value = value.replace(secret, REDACTED)
        value = _URL.sub(lambda match: self.url(match.group()), value)
        value = _ASSIGNMENT.sub(lambda match: match[1] + REDACTED, value)
        value = _BEARER.sub(lambda match: match[1] + " " + REDACTED, value)
        # Preserve tokens already emitted by the turn's pseudonymizer.
        parts = _TOKEN.split(value)
        tokens = _TOKEN.findall(value)
        value = "".join(
            self.pseudonymizer.mask(part) + (tokens[i] if i < len(tokens) else "")
            for i, part in enumerate(parts)
        )
        if not bounded:
            return value
        raw = value.encode("utf-8")
        limit = min(self.remaining, 64 * 1024)
        self.remaining -= min(len(raw), limit)
        if len(raw) > limit:
            self.truncated = True
            return raw[:limit].decode("utf-8", errors="ignore") + "[truncated]"
        return value

    @staticmethod
    def url(value: str) -> str:
        try:
            parts = urlsplit(value)
            authority = parts.netloc.rsplit("@", 1)[-1]
            query = "&".join(f"{quote(key)}={REDACTED}" for key, _ in parse_qsl(parts.query))
            return urlunsplit((parts.scheme, authority, parts.path, query, ""))
        except ValueError:
            return REDACTED

    def clean(self, value: object, depth: int = 0) -> object:
        if depth > 30:
            self.truncated = True
            return "[truncated]"
        if isinstance(value, dict):
            return {
                self.text(str(key), bounded=False): REDACTED if (_SENSITIVE.search(str(key)) and str(key) not in _TOKEN_COUNTS)
                else self.clean(item, depth + 1)
                for key, item in value.items()
            }
        if isinstance(value, list | tuple):
            return [self.clean(item, depth + 1) for item in value]
        if isinstance(value, str):
            # Tool content often contains JSON with credential-shaped keys.
            if value.lstrip().startswith(("{", "[")):
                try:
                    parsed = json.loads(value)
                except ValueError:
                    pass
                else:
                    if isinstance(parsed, dict | list):
                        return json.dumps(self.clean(parsed, depth + 1), ensure_ascii=False)
            return self.text(value)
        return REDACTED if type(value) in (int, float) and str(value) in self.secrets else value


def integration_secrets(integrations) -> list[str]:
    values = []
    for integration in integrations:
        if integration.secret:
            values.append(integration.secret)
        values.extend(stored_secret_headers(integration).values())
        values.extend(
            str(header.get("value", "")) for header in integration.config.get("headers", [])
        )
        for key in ("url", "base_url"):
            try:
                parts = urlsplit(str(integration.config.get(key, "")))
                values.extend(value for _, value in parse_qsl(parts.query))
                values.extend(filter(None, (parts.username, parts.password)))
            except ValueError:
                continue
    return values
