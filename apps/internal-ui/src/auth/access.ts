import type { RouteKey, SessionUser } from "../types";

type RouteAccess = { capability: string; departmentCode?: string };

const ROUTE_ACCESS: Partial<Record<RouteKey, RouteAccess>> = {
  accessProfiles: { capability: "employees.manage" },
  administrationOrganization: { capability: "settings.view" },
  administrationSubscription: { capability: "settings.view" },
  administrationAudit: { capability: "audit.view" },
  command: { capability: "company.view" },
  departments: { capability: "departments.view" },
  employees: { capability: "employees.view" },
  employeeDetail: { capability: "employees.view" },
  aiAgents: { capability: "ai.view" },
  aiAgentCreate: { capability: "ai.manage" },
  aiAgentDetail: { capability: "ai.view" },
  aiKnowledge: { capability: "ai.view" },
  aiKnowledgeCreate: { capability: "ai.manage" },
  aiKnowledgeDetail: { capability: "ai.view" },
  aiUsage: { capability: "ai.view" },
  integrations: { capability: "integrations.view" },
  channels: { capability: "channels.view" },
  channelCreate: { capability: "channels.manage" },
  channelDetail: { capability: "channels.view" },
  salesDialogs: { capability: "conversations.view", departmentCode: "sales" },
  salesClients: { capability: "customers.view", departmentCode: "sales" },
  salesClientDetail: { capability: "customers.view", departmentCode: "sales" },
  supportOverview: { capability: "support.view", departmentCode: "support" },
  supportDialogs: { capability: "conversations.view", departmentCode: "support" },
  supportPortals: { capability: "support.view", departmentCode: "support" },
  supportPortalDetail: { capability: "support.view", departmentCode: "support" },
};

export function hasCapability(
  user: SessionUser,
  capability: string,
  departmentCode?: string,
): boolean {
  if (!user.capabilities.includes(capability)) return false;
  return user.accessScopes.some((scope) => {
    if (!scope.capabilities.includes(capability)) return false;
    if (scope.scopeType === "ORGANIZATION") return true;
    return Boolean(departmentCode) && scope.departmentCode === departmentCode;
  });
}

/**
 * Отделы, которыми ограничен доступ пользователя к возможности.
 *
 * `null` — доступ на всю организацию. Непустой список означает, что данные
 * приходят подмножеством, и интерфейс обязан сказать об этом явно, иначе
 * пользователь примет отфильтрованный список за полный.
 */
export function scopeDepartments(user: SessionUser, capability: string): string[] | null {
  const scopes = user.accessScopes.filter((scope) => scope.capabilities.includes(capability));
  if (scopes.some((scope) => scope.scopeType === "ORGANIZATION")) return null;
  return [...new Set(
    scopes.map((scope) => scope.departmentCode).filter((code): code is string => Boolean(code)),
  )];
}

export function canAccess(user: SessionUser, route: RouteKey): boolean {
  if (route === "profile" || route === "settings") return true;
  if (route === "administrationSubscription" && user.deliveryMode !== "CLOUD") {
    return false;
  }
  const requirement = ROUTE_ACCESS[route];
  return requirement
    ? hasCapability(user, requirement.capability, requirement.departmentCode)
    : false;
}

const LANDING_PRIORITY: RouteKey[] = [
  "command",
  "salesDialogs",
  "supportDialogs",
  "supportOverview",
  "employees",
  "supportPortals",
  "aiAgents",
  "integrations",
];

export function defaultRoute(user: SessionUser): RouteKey {
  return LANDING_PRIORITY.find((route) => canAccess(user, route)) ?? "profile";
}
