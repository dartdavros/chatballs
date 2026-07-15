from __future__ import annotations

import hashlib
import secrets

from django.db import transaction
from django.utils import timezone

from hub_platform.platform.capabilities import is_valid_platform_capability
from hub_platform.platform.models import PlatformOperator, PlatformToken

_TOKEN_SCHEME = "ctp"  # custocrm-platform; makes platform tokens visually distinct


def hash_token(token: str) -> str:
    """sha256 hex digest. Mirrors identity invitation token hashing."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token_value() -> str:
    return f"{_TOKEN_SCHEME}_{secrets.token_urlsafe(32)}"


@transaction.atomic
def issue_platform_token(
    *,
    operator: PlatformOperator,
    name: str,
    capabilities: list[str],
) -> tuple[PlatformToken, str]:
    """Create a token; plaintext is returned once to the caller and never stored."""
    for code in capabilities:
        if not is_valid_platform_capability(code):
            raise ValueError(f"Unknown platform capability: {code}")
    plaintext = generate_token_value()
    token = PlatformToken.objects.create(
        operator=operator,
        name=name,
        token_hash=hash_token(plaintext),
        capabilities=list(dict.fromkeys(capabilities)),
    )
    return token, plaintext


def authenticate_token(raw_token: str) -> PlatformToken | None:
    """Resolve an opaque token to a non-revoked, active-operator token or None."""
    if not raw_token or not raw_token.startswith(f"{_TOKEN_SCHEME}_"):
        return None
    token = (
        PlatformToken.objects.select_related("operator")
        .filter(token_hash=hash_token(raw_token), revoked_at__isnull=True)
        .first()
    )
    if token is None or not token.operator.is_active:
        return None
    PlatformToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
    return token
