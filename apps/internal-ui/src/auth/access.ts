import type { RouteKey, SessionUser } from "../types";

// Ролевая модель SPEC-CHATBALLS-0031 §3: OWNER и ADMIN идентичны и видят всё,
// EMPLOYEE работает только в чате. Backend — источник истины (deny-by-default);
// фронтенд лишь скрывает недоступное.

const EMPLOYEE_ROUTES: ReadonlySet<RouteKey> = new Set<RouteKey>([
  "chat",
  "profile",
]);

export function isManager(user: SessionUser): boolean {
  return user.role === "OWNER" || user.role === "ADMIN";
}

export function hasCapability(user: SessionUser, capability: string): boolean {
  return user.capabilities.includes(capability);
}

/** Кто заводит новые организации: администратор установки и тот, кто где-либо
 *  владелец или администратор. Роль в текущей организации не решает —
 *  сотрудник здесь может быть владельцем в другой. Сервер проверяет то же. */
export function canCreateOrganization(user: SessionUser): boolean {
  return user.isInstanceAdmin || user.memberships.some((membership) => membership.role === "OWNER" || membership.role === "ADMIN");
}

export function canAccess(user: SessionUser, route: RouteKey): boolean {
  // «Настройки» — настройки организации: только владелец и админ. Личные
  // параметры сотрудника живут на странице «Профиль» (дизайн-базлайн v2).
  if (route === "profile") return true;
  if (route === "organizationCreate") return canCreateOrganization(user);
  if (isManager(user)) return true;
  return EMPLOYEE_ROUTES.has(route);
}

export function defaultRoute(user: SessionUser): RouteKey {
  return "chat";
}
