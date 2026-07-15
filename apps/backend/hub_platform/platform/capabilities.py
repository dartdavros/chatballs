from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformCapabilitySpec:
    code: str
    name: str
    description: str


# Global platform capabilities (ADR-HUB-0031 §9). Distinct from the tenant
# capability registry (identity/capabilities.py): a platform capability is held
# by a PlatformOperator/token and is never derived from an OrganizationMembership.
_PLATFORM_CAPABILITIES = (
    PlatformCapabilitySpec(
        code="platform.organizations.provision",
        name="Provision organizations",
        description="Create a new tenant organization via the Platform API",
    ),
)

PLATFORM_CAPABILITIES = {spec.code: spec for spec in _PLATFORM_CAPABILITIES}


def platform_capability_spec(code: str) -> PlatformCapabilitySpec:
    try:
        return PLATFORM_CAPABILITIES[code]
    except KeyError as error:
        raise ValueError(f"Unknown platform capability: {code}") from error


def is_valid_platform_capability(code: str) -> bool:
    return code in PLATFORM_CAPABILITIES
