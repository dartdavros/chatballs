from __future__ import annotations

from typing import Any

from chatballs.identity.models import Organization, OrganizationMembership
from chatballs.platform.models import OrganizationProvisioning
from chatballs.platform.provisioning_models import ProvisioningStatus

_PROVISIONING_SOURCE_DEFAULT = "PLATFORM_OPERATOR"


def provisioning_result_payload(
    *,
    provisioning: OrganizationProvisioning,
    organization: Organization,
    owner_state: str,
) -> dict[str, Any]:
    """Response shape for POST /api/v1/organizations. Never includes secrets,
    tokens or invitation plaintext (SPEC-HUB-0021 §12/§13)."""
    return {
        "organization": {
            "publicId": str(organization.public_id),
            "name": organization.name,
            "slug": organization.slug,
            "status": organization.status,
            "timezone": organization.timezone,
            "currency": organization.currency,
        },
        "provisioning": {
            "status": provisioning.status,
            "source": provisioning.source,
            "idempotencyKey": provisioning.idempotency_key,
        },
        "owner": {"state": owner_state},
    }


def owner_state_for(
    organization: Organization, membership: OrganizationMembership | None
) -> str:
    """ACTIVE when an OWNER membership exists, otherwise PENDING_INVITATION."""
    if organization.status == ProvisioningStatus.WAITING_FOR_OWNER:
        return "pending_invitation"
    if membership is not None:
        return "active"
    return "pending_invitation"
