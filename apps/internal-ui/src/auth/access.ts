import type { RouteKey, SessionUser } from "../types";

// Ролевая модель SPEC-HUB-0031 §3: OWNER и ADMIN идентичны и видят всё,
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

export function canAccess(user: SessionUser, route: RouteKey): boolean {
  // «Настройки» — настройки организации: только владелец и админ. Личные
  // параметры сотрудника живут на странице «Профиль» (дизайн-базлайн v2).
  if (route === "profile") return true;
  if (isManager(user)) return true;
  return EMPLOYEE_ROUTES.has(route);
}

export function defaultRoute(user: SessionUser): RouteKey {
  return "chat";
}
