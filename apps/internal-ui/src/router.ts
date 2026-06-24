import type { RouteKey } from "./types";

export type RouteState = {
  route: RouteKey;
  employeeId: number | null;
  productId: number | null;
};

export function routeFromPath(pathname: string): RouteState {
  const path = pathname.replace(/\/+$/, "") || "/";
  const base = { employeeId: null, productId: null };
  if (path === "/" || path === "/command") return { route: "command", ...base };
  if (path === "/departments") return { route: "departments", ...base };
  if (path === "/departments/sales") return { route: "salesOverview", ...base };
  if (path === "/departments/sales/clients") return { route: "salesClients", ...base };
  if (path === "/departments/sales/clients/CUS-4702") return { route: "salesClientDetail", ...base };
  if (path === "/departments/sales/dialogs") return { route: "salesDialogs", ...base };
  if (path === "/departments/sales/orders") return { route: "salesOrders", ...base };
  if (path === "/departments/sales/orders/ORD-10519") return { route: "salesOrderDetail", ...base };
  if (path === "/employees") return { route: "employees", ...base };
  if (path.startsWith("/employees/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { route: "employeeDetail", employeeId: id, productId: null } : { route: "employees", ...base };
  }
  if (path === "/products") return { route: "products", ...base };
  if (path.startsWith("/products/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { route: "productDetail", employeeId: null, productId: id } : { route: "products", ...base };
  }
  if (path === "/ai" || path === "/ai/agents") return { route: "aiAgents", ...base };
  if (path === "/ai/test-chat") return { route: "aiTestChat", ...base };
  if (path === "/ai/usage") return { route: "aiUsage", ...base };
  if (path === "/profile") return { route: "profile", ...base };
  return { route: "command", ...base };
}

export function pathFromRoute(route: RouteKey, entityId: number | null = null): string {
  if (route === "command") return "/";
  if (route === "departments") return "/departments";
  if (route === "salesOverview") return "/departments/sales";
  if (route === "salesClients") return "/departments/sales/clients";
  if (route === "salesClientDetail") return "/departments/sales/clients/CUS-4702";
  if (route === "salesDialogs") return "/departments/sales/dialogs";
  if (route === "salesOrders") return "/departments/sales/orders";
  if (route === "salesOrderDetail") return "/departments/sales/orders/ORD-10519";
  if (route === "employees") return "/employees";
  if (route === "employeeDetail") return entityId ? `/employees/${entityId}` : "/employees";
  if (route === "products") return "/products";
  if (route === "productDetail") return entityId ? `/products/${entityId}` : "/products";
  if (route === "aiAgents") return "/ai/agents";
  if (route === "aiTestChat") return "/ai/test-chat";
  if (route === "aiUsage") return "/ai/usage";
  if (route === "aiAgentDetail") return entityId ? `/ai/agents/${entityId}` : "/ai/agents";
  if (route === "aiRelease") return entityId ? `/ai/releases/${entityId}` : "/ai/agents";
  if (route === "profile") return "/profile";
  return "/profile";
}
