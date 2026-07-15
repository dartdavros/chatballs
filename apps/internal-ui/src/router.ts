import type { RouteKey } from "./types";

export type RouteState = {
  organizationPublicId: string | null;
  route: RouteKey;
  employeeId: number | null;
  productId: number | null;
  productCode: string | null;
  agentId: number | null;
  knowledgeId: number | null;
  clientId: number | null;
  orderId: number | null;
};

export function routeFromPath(pathname: string, search = ""): RouteState {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const match = normalized.match(/^\/organizations\/([0-9a-f-]{36})(\/.*)?$/i);
  const organizationPublicId = match?.[1] ?? null;
  const path = match ? match[2] || "/" : normalized;
  const base = { employeeId: null, productId: null, productCode: null, agentId: null, knowledgeId: null, clientId: null, orderId: null };
  const state = { organizationPublicId, ...base };
  if (path === "/" || path === "/command") return { route: "command", ...state };
  if (path === "/departments") return { route: "departments", ...state };
  if (path === "/departments/sales") return { route: "salesOverview", ...state };
  if (path === "/departments/support") return { route: "supportOverview", ...state };
  if (path === "/departments/support/dialogs") return { route: "supportDialogs", ...state };
  if (path === "/departments/sales/clients") return { route: "salesClients", ...state };
  if (path.startsWith("/departments/sales/clients/")) {
    const id = Number(path.split("/")[4]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "salesClientDetail", clientId: id } : { route: "salesClients", ...state };
  }
  if (path === "/departments/sales/dialogs") return { route: "salesDialogs", ...state };
  if (path === "/departments/sales/orders") return { route: "salesOrders", ...state };
  if (path.startsWith("/departments/sales/orders/")) {
    const id = Number(path.split("/")[4]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "salesOrderDetail", orderId: id } : { route: "salesOrders", ...state };
  }
  if (path === "/employees") return { route: "employees", ...state };
  if (path === "/employees/access-profiles") return { route: "accessProfiles", ...state };
  if (path.startsWith("/employees/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "employeeDetail", employeeId: id } : { route: "employees", ...state };
  }
  if (path === "/products") return { route: "products", ...state };
  if (path.startsWith("/products/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "productDetail", productId: id } : { route: "products", ...state };
  }
  if (path === "/ai" || path === "/ai/agents") return { route: "aiAgents", ...state };
  if (path === "/ai/agents/new") {
    const productCode = new URLSearchParams(search).get("product");
    return { route: "aiAgentCreate", ...state, productCode };
  }
  if (path.startsWith("/ai/agents/")) {
    const id = Number(path.split("/")[3]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "aiAgentDetail", agentId: id } : { route: "aiAgents", ...state };
  }
  if (path === "/ai/knowledge") return { route: "aiKnowledge", ...state };
  if (path.startsWith("/ai/knowledge/")) {
    const id = Number(path.split("/")[3]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "aiKnowledgeDetail", knowledgeId: id } : { route: "aiKnowledge", ...state };
  }
  if (path === "/ai/usage") return { route: "aiUsage", ...state };
  if (path === "/integrations") return { route: "integrations", ...state };
  if (path === "/profile") return { route: "profile", ...state };
  return { route: "command", ...state };
}

export function pathFromRoute(route: RouteKey, entityId: number | null = null, productCode: string | null = null, organizationPublicId: string | null = null): string {
  const prefix = organizationPublicId ? `/organizations/${organizationPublicId}` : "";
  if (route === "command") return `${prefix}/`;
  if (route === "departments") return `${prefix}/departments`;
  if (route === "salesOverview") return `${prefix}/departments/sales`;
  if (route === "supportOverview") return `${prefix}/departments/support`;
  if (route === "supportDialogs") return `${prefix}/departments/support/dialogs`;
  if (route === "salesClients") return `${prefix}/departments/sales/clients`;
  if (route === "salesClientDetail") return entityId ? `${prefix}/departments/sales/clients/${entityId}` : `${prefix}/departments/sales/clients`;
  if (route === "salesDialogs") return `${prefix}/departments/sales/dialogs`;
  if (route === "salesOrders") return `${prefix}/departments/sales/orders`;
  if (route === "salesOrderDetail") return entityId ? `${prefix}/departments/sales/orders/${entityId}` : `${prefix}/departments/sales/orders`;
  if (route === "employees") return `${prefix}/employees`;
  if (route === "accessProfiles") return `${prefix}/employees/access-profiles`;
  if (route === "employeeDetail") return entityId ? `${prefix}/employees/${entityId}` : `${prefix}/employees`;
  if (route === "products") return `${prefix}/products`;
  if (route === "productDetail") return entityId ? `${prefix}/products/${entityId}` : `${prefix}/products`;
  if (route === "aiAgents") return `${prefix}/ai/agents`;
  if (route === "aiAgentCreate") return productCode ? `${prefix}/ai/agents/new?product=${encodeURIComponent(productCode)}` : `${prefix}/ai/agents/new`;
  if (route === "aiUsage") return `${prefix}/ai/usage`;
  if (route === "aiAgentDetail") return entityId ? `${prefix}/ai/agents/${entityId}` : `${prefix}/ai/agents`;
  if (route === "aiKnowledge") return `${prefix}/ai/knowledge`;
  if (route === "aiKnowledgeDetail") return entityId ? `${prefix}/ai/knowledge/${entityId}` : `${prefix}/ai/knowledge`;
  if (route === "integrations") return `${prefix}/integrations`;
  if (route === "profile") return `${prefix}/profile`;
  return `${prefix}/profile`;
}
