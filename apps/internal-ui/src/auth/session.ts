import type { AuthenticatedUser, SessionUser } from "../types";

const preferenceKey = "chatbolls.organizationPublicId";

export function activateOrganization(
  identity: AuthenticatedUser,
  requestedPublicId: string | null,
): SessionUser | null {
  const preferred = requestedPublicId || window.sessionStorage.getItem(preferenceKey);
  const membership =
    identity.memberships.find((item) => item.organizationPublicId === preferred) ||
    (identity.memberships.length === 1 ? identity.memberships[0] : null);
  if (!membership) return null;
  window.sessionStorage.setItem(preferenceKey, membership.organizationPublicId);
  return { ...identity, ...membership };
}

export function clearOrganizationPreference(): void {
  window.sessionStorage.removeItem(preferenceKey);
}
