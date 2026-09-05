from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from chatballs.identity.models import Organization
from chatballs.platform.provisioning_models import (
    OrganizationProvisioning,
    ProvisioningSource,
    ProvisioningStatus,
)


@dataclass(frozen=True)
class ProvisioningCommand:
    organization_name: str
    organization_slug: str
    owner_email: str
    source: str
    idempotency_key: str
    timezone: str = "Europe/Moscow"
    currency: str = "RUB"
    locale: str = ""
    legal_name: str = ""
    tax_profile: dict[str, Any] | None = None

    def significant_fields(self) -> dict[str, Any]:
        """Canonical normalized values for request_hash (SPEC-HUB-0021 §11):
        transport metadata is excluded. Keys are sorted for a stable hash."""
        data = asdict(self)
        data["owner_email"] = data["owner_email"].strip().lower()
        data["organization_slug"] = data["organization_slug"].strip().lower()
        data["organization_name"] = data["organization_name"].strip()
        # Drop empty optional fields so their absence vs default do not diverge.
        return {k: v for k, v in sorted(data.items()) if not _is_empty(v)}

    def request_hash(self) -> str:
        payload = json.dumps(self.significant_fields(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_empty(value: Any) -> bool:
    return value in ("", None, {}, [])


@dataclass(frozen=True)
class ProvisioningResult:
    provisioning: OrganizationProvisioning
    organization: Organization
    created: bool  # False on idempotent replay


def is_replay(provisioning: OrganizationProvisioning, command: ProvisioningCommand) -> bool:
    """COMPLETED/WAITING_FOR_OWNER with a matching request hash is an idempotent
    replay; a differing hash is a conflict (SPEC-HUB-0021 §11)."""
    return provisioning.request_hash == command.request_hash()


_TERMINAL_STATUSES = {ProvisioningStatus.COMPLETED, ProvisioningStatus.WAITING_FOR_OWNER}


def is_terminal(provisioning: OrganizationProvisioning) -> bool:
    return provisioning.status in _TERMINAL_STATUSES


def allowed_source(source: str) -> bool:
    return source in ProvisioningSource.values
