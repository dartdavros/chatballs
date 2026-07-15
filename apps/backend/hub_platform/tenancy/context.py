from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from hub_platform.events.context import get_correlation_id

if TYPE_CHECKING:
    from hub_platform.identity.models import HumanUser, Organization, OrganizationMembership


class TenantActorKind(StrEnum):
    HUMAN = "HUMAN"
    MACHINE = "MACHINE"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Canonical organization boundary carried through one operation."""

    organization: Organization
    membership: OrganizationMembership | None
    actor_user: HumanUser | None
    actor_kind: TenantActorKind
    correlation_id: str

    @property
    def organization_id(self) -> int:
        return self.organization.pk

    @property
    def membership_id(self) -> int | None:
        return self.membership.pk if self.membership is not None else None

    @classmethod
    def for_membership(
        cls,
        membership: OrganizationMembership,
        *,
        correlation_id: str | None = None,
    ) -> TenantContext:
        return cls(
            organization=membership.organization,
            membership=membership,
            actor_user=membership.user,
            actor_kind=TenantActorKind.HUMAN,
            correlation_id=correlation_id or get_correlation_id(),
        )

    @classmethod
    def for_resource(
        cls,
        organization: Organization,
        *,
        actor_kind: TenantActorKind = TenantActorKind.MACHINE,
        actor_user: HumanUser | None = None,
        correlation_id: str | None = None,
    ) -> TenantContext:
        return cls(
            organization=organization,
            membership=None,
            actor_user=actor_user,
            actor_kind=actor_kind,
            correlation_id=correlation_id or get_correlation_id(),
        )
