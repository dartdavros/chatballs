import type { RouteKey, SessionUser } from "../types";

// Ролевая модель SPEC-CHATBALLS-0031 §3: OWNER и ADMIN идентичны и видят всё,
// EMPLOYEE работает только в чате. Backend — источник истины (deny-by-default);
// фронтенд лишь скрывает недоступное.

const EMPLOYEE_ROUTES: ReadonlySet<RouteKey> = new Set<RouteKey>([
  "chat",
  "profile",
  "replyTemplates",
]);

export function canManagePlatform(user: SessionUser): boolean {
  return user.canManagePlatform ?? user.isInstanceAdmin;
}

export function isManager(user: SessionUser): boolean {
  return user.role === "OWNER" || user.role === "ADMIN";
}

export function canViewReports(access: { reportCapabilities?: string[] }): boolean {
  return access.reportCapabilities?.includes("reports.view") ?? false;
}

export function hasCapability(user: SessionUser, capability: string): boolean {
  return user.capabilities.includes(capability);
}

export function canViewRuleJournal(user: SessionUser): boolean {
  return isManager(user) || user.role === "SUPERVISOR" && (user.supervisedGroups?.length ?? 0) > 0;
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
  if (route === "ruleJournal") return canViewRuleJournal(user);
  if (isManager(user)) return true;
  if (route === "supportReports") return canViewReports(user);
  if (route === "qualityAnalysis" && user.role === "SUPERVISOR") return true;
  return EMPLOYEE_ROUTES.has(route);
}

export function defaultRoute(user: SessionUser): RouteKey {
  return "chat";
}
