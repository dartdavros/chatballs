from __future__ import annotations

from typing import Any

from hub_platform.platform.provisioning_command import ProvisioningCommand
from hub_platform.platform.provisioning_models import ProvisioningSource

_REQUIRED_FIELDS = (
    "name",
    "slug",
    "owner_email",
    "timezone",
    "currency",
)


def parse_provisioning_body(
    body: Any, *, idempotency_key: str, source: str
) -> tuple[ProvisioningCommand, str | None]:
    """Map the API body (SPEC-HUB-0021 §12) to a ProvisioningCommand. Returns
    (command, error_message). Validation is intentionally explicit (no DRF
    serializers), mirroring identity/access_payloads.py."""
    if not isinstance(body, dict):
        return _empty_command(idempotency_key, source), "Request body must be an object"
    for field in _REQUIRED_FIELDS:
        if field not in body:
            return _empty_command(idempotency_key, source), f"{field} is required"
    command = ProvisioningCommand(
        organization_name=str(body.get("name", "")),
        organization_slug=str(body.get("slug", "")),
        owner_email=str(body.get("owner_email", "")),
        source=source,
        idempotency_key=idempotency_key,
        timezone=str(body.get("timezone", "Europe/Moscow")),
        currency=str(body.get("currency", "RUB")),
        locale=str(body.get("locale", "")),
        legal_name=str(body.get("legal_name", "")),
        tax_profile=body.get("tax_profile") if isinstance(body.get("tax_profile"), dict) else None,
    )
    if not _valid_source(source):
        return command, f"Unsupported source: {source}"
    return command, None


def _valid_source(source: str) -> bool:
    return source in ProvisioningSource.values


def _empty_command(idempotency_key: str, source: str) -> ProvisioningCommand:
    return ProvisioningCommand(
        organization_name="",
        organization_slug="",
        owner_email="",
        source=source,
        idempotency_key=idempotency_key,
    )
