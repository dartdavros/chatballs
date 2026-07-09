import type { Role, RouteKey } from "../types";

// Матрица доступа SPEC-HUB-0004 §9 + SPEC-HUB-0010 §8.1/§10. OWNER имеет сквозной
// доступ; OPERATOR работает только в пространстве своего отдела и личном профиле.
// Department-scoped: sales operator видит только sales, support operator — только
// support (изоляция inbox §10). §8.1 (оператор в нескольких отделах) не покрыт —
// оператор строго в одном отделе (одиночный FK department на backend).
const SALES_ROUTES: ReadonlySet<RouteKey> = new Set<RouteKey>([
  "salesOverview",
  "salesDialogs",
  "salesClients",
  "salesClientDetail",
  "salesOrders",
  "salesOrderDetail",
]);

const SUPPORT_ROUTES: ReadonlySet<RouteKey> = new Set<RouteKey>([
  "supportOverview",
  "supportDialogs",
]);

export function canAccess(role: Role, route: RouteKey, department?: string | null): boolean {
  if (role === "OWNER") return true;
  if (route === "profile") return true;
  if (department === "support") return SUPPORT_ROUTES.has(route);
  // По умолчанию OPERATOR — sales-пространство (обратная совместимость).
  return SALES_ROUTES.has(route);
}

// SPEC-HUB-0004 §11 + SPEC-HUB-0010 §8.1: OWNER — командный центр; OPERATOR —
// диалоги своего отдела (support operator попадает в support dialogs).
export function defaultRoute(role: Role, department?: string | null): RouteKey {
  if (role === "OWNER") return "command";
  return department === "support" ? "supportDialogs" : "salesDialogs";
}

