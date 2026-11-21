"""HTTPS transport and response contract for the public installation check-in."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from unicodedata import category
from urllib.parse import urlsplit
from uuid import UUID

import httpx

CHECK_IN_URL = "https://bo.chatballs.ru/public/v1/installations/check-in/"
TIMEOUT_SECONDS = 5
DAILY_INTERVAL = timedelta(days=1)
RETRY_INTERVAL = timedelta(minutes=15)


@dataclass(frozen=True)
class CheckInResult:
    error: str = ""
    delay: timedelta = DAILY_INTERVAL
    announcements: list[dict] | None = None


def _safe_link(value: str) -> str:
    if not value or any(char.isspace() or category(char) == "Cc" or char == "\\" for char in value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or "@" in parsed.netloc:
            return ""
        if "%" in parsed.hostname or parsed.port == 0:
            return ""
        httpx.URL(value)
    except (ValueError, httpx.InvalidURL):
        return ""
    return value


def parse_announcements(payload: object) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("announcements"), list):
        raise ValueError("Invalid announcements")
    announcements = []
    for item in payload["announcements"]:
        if (
            not isinstance(item, dict)
            or type(item.get("id")) is not int
            or any(not isinstance(item.get(key), str) for key in ("title", "text", "link"))
            or any("\x00" in item[key] for key in ("title", "text"))
        ):
            raise ValueError("Invalid announcement")
        # PostgreSQL JSONB requires Unicode scalars and cannot encode U+0000.
        for key in ("title", "text"):
            item[key].encode("utf-8")
        announcements.append({
            "id": item["id"], "title": item["title"], "text": item["text"],
            "link": _safe_link(item["link"]),
        })
    return announcements


def _rate_limit_delay(value: str) -> timedelta:
    value = value.strip()
    if value.isascii() and value.isdecimal():
        # Beyond the longest representable PostgreSQL application timestamp,
        # the store saturates the deadline instead of retrying prematurely.
        seconds = value.lstrip("0") or "0"
        upper_bound = 10**12
        delay = int(seconds) if len(seconds) < 13 else upper_bound
        return max(RETRY_INTERVAL, timedelta(seconds=delay))
    return RETRY_INTERVAL


async def _post(installation_id: UUID, version: str) -> CheckInResult:
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            async with httpx.AsyncClient(
                verify=True, follow_redirects=False, trust_env=False, timeout=TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    CHECK_IN_URL,
                    json={"installation_id": str(installation_id), "version": version},
                )
    except (TimeoutError, httpx.TimeoutException):
        return CheckInResult(error="timeout", delay=RETRY_INTERVAL)
    except httpx.HTTPError:
        return CheckInResult(error="network", delay=RETRY_INTERVAL)

    status = response.status_code
    if status == 200:
        try:
            return CheckInResult(announcements=parse_announcements(response.json()))
        except (ValueError, RecursionError):
            return CheckInResult(error="invalid_response")
    if status == 429:
        return CheckInResult(error="http_429", delay=_rate_limit_delay(response.headers.get("Retry-After", "")))
    return CheckInResult(
        error=f"http_{status}",
        delay=RETRY_INTERVAL if 500 <= status < 600 else DAILY_INTERVAL,
    )


def send_check_in(installation_id: UUID, version: str) -> CheckInResult:
    if not 1 <= len(version) <= 255 or any(category(char) in {"Cc", "Cs"} for char in version):
        return CheckInResult(error="invalid_version")
    return asyncio.run(_post(installation_id, version))
