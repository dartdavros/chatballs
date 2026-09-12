import type { AuthenticatedUser, SessionUser } from "../types";

const preferenceKey = "chatballs.organizationPublicId";

function storedPreference(): string | null {
  try {
    return window.localStorage.getItem(preferenceKey);
  } catch {
    return null;
  }
}

function rememberPreference(publicId: string): void {
  try {
    window.localStorage.setItem(preferenceKey, publicId);
  } catch {
    // Хранилище недоступно (приватный режим, запрет сайта) — адрес всё равно
    // несёт организацию, а без него откроется первая по списку.
  }
}

/** Выбрать организацию сессии: из адреса, иначе последнюю открытую, иначе
 *  первую в списке членств (сервер отдаёт их по имени). Человек с несколькими
 *  организациями не упирается в «нет доступа» — он входит в одну из своих и
 *  меняет её переключателем в сайдбаре (дизайн-базлайн v2, A1). */
export function activateOrganization(
  identity: AuthenticatedUser,
  requestedPublicId: string | null,
): SessionUser | null {
  const byId = (publicId: string | null) =>
    publicId ? identity.memberships.find((item) => item.organizationPublicId === publicId) : undefined;
  const membership = byId(requestedPublicId) || byId(storedPreference()) || identity.memberships[0];
  if (!membership) return null;
  rememberPreference(membership.organizationPublicId);
  return { ...identity, ...membership };
}

export function clearOrganizationPreference(): void {
  try {
    window.localStorage.removeItem(preferenceKey);
  } catch {
    // См. rememberPreference.
  }
}
