from __future__ import annotations

from hub_platform.identity.models import HumanUser, OrganizationMembership


def single_membership_for_user(user: HumanUser) -> OrganizationMembership | None:
    """C02 bridge for routes that do not yet carry an explicit tenant context.

    Returning ``None`` for both zero and multiple memberships keeps legacy routes
    fail-closed. C03 replaces this bridge with an explicit organization route.
    """

    try:
        return user.memberships.select_related("organization", "primary_department").get()
    except (
        OrganizationMembership.DoesNotExist,
        OrganizationMembership.MultipleObjectsReturned,
    ):
        return None
