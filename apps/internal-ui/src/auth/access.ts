import type { RouteKey, SessionUser } from "../types";

type RouteAccess = { capability: string; departmentCode?: string };

const ROUTE_ACCESS: Partial<Record<RouteKey, RouteAccess>> = {
  accessProfiles: { capability: "employees.manage" },
  command: { capability: "company.view" },
  departments: { capability: "departments.view" },
  employees: { capability: "employees.view" },
  employeeDetail: { capability: "employees.view" },
  products: { capability: "products.view" },
  productDetail: { capability: "products.view" },
  aiAgents: { capability: "ai.view" },
  aiAgentCreate: { capability: "ai.manage" },
  aiAgentDetail: { capability: "ai.view" },
  aiKnowledge: { capability: "ai.view" },
  aiKnowledgeDetail: { capability: "ai.view" },
  aiUsage: { capability: "ai.view" },
  integrations: { capability: "integrations.view" },
  salesOverview: { capability: "sales.view", departmentCode: "sales" },
  salesDialogs: { capability: "conversations.view", departmentCode: "sales" },
  salesClients: { capability: "customers.view", departmentCode: "sales" },
  salesClientDetail: { capability: "customers.view", departmentCode: "sales" },
  salesOrders: { capability: "sales.view", departmentCode: "sales" },
  salesOrderDetail: { capability: "sales.view", departmentCode: "sales" },
  supportOverview: { capability: "support.view", departmentCode: "support" },
  supportDialogs: { capability: "conversations.view", departmentCode: "support" },
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

export function canAccess(user: SessionUser, route: RouteKey): boolean {
  if (route === "profile" || route === "settings") return true;
  const requirement = ROUTE_ACCESS[route];
  return requirement
    ? hasCapability(user, requirement.capability, requirement.departmentCode)
    : false;
}

const LANDING_PRIORITY: RouteKey[] = [
  "command",
  "salesDialogs",
  "supportDialogs",
  "salesOverview",
  "supportOverview",
  "employees",
  "products",
  "aiAgents",
  "integrations",
];

export function defaultRoute(user: SessionUser): RouteKey {
  return LANDING_PRIORITY.find((route) => canAccess(user, route)) ?? "profile";
}
