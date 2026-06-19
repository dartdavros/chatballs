import type { Role, RouteKey } from "../types";

// Матрица доступа SPEC-HUB-0004 §9. OWNER имеет сквозной доступ;
// OPERATOR работает только в пространстве продаж и личном профиле.
const OPERATOR_ROUTES: ReadonlySet<RouteKey> = new Set<RouteKey>([
  "salesOverview",
  "salesDialogs",
  "salesClients",
  "salesClientDetail",
  "salesOrders",
  "salesOrderDetail",
  "profile",
]);

export function canAccess(role: Role, route: RouteKey): boolean {
  if (role === "OWNER") return true;
  return OPERATOR_ROUTES.has(route);
}

// SPEC-HUB-0004 §11: после входа OWNER попадает в командный центр,
// OPERATOR — в диалоги отдела продаж.
export function defaultRoute(role: Role): RouteKey {
  return role === "OWNER" ? "command" : "salesDialogs";
}
