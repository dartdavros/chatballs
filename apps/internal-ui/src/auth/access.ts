import type { Role, RouteKey } from "../types";

// Матрица доступа SPEC-HUB-0004 §9 + SPEC-HUB-0010 §8.1/§10. OWNER имеет сквозной
// доступ; EMPLOYEE работает только в пространстве своего отдела и личном профиле.
// Compat-адаптер этапа 1 (ADR-HUB-0027): операционный доступ по-прежнему определяется
// department. Полная capability-модель придёт на этапе 3. Department-scoped: sales →
// только sales, support → только support (изоляция inbox §10). §8.1 (несколько
// отделов) не покрыт — сотрудник строго в одном основном отделе (одиночный FK).
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
  // Административный уровень (ADR-HUB-0027 этап 2): ADMIN имеет все обычные capability
  // организации наравне с OWNER, поэтому получает сквозной доступ к интерфейсу.
  if (role === "OWNER" || role === "ADMIN") return true;
  if (route === "profile") return true;
  if (department === "support") return SUPPORT_ROUTES.has(route);
  // По умолчанию EMPLOYEE — sales-пространство (обратная совместимость).
  return SALES_ROUTES.has(route);
}

// SPEC-HUB-0004 §11 + SPEC-HUB-0010 §8.1: OWNER/ADMIN — командный центр; EMPLOYEE —
// диалоги своего отдела (support operator попадает в support dialogs).
export function defaultRoute(role: Role, department?: string | null): RouteKey {
  if (role === "OWNER" || role === "ADMIN") return "command";
  return department === "support" ? "supportDialogs" : "salesDialogs";
}

