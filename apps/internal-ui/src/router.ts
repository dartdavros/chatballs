import type { RouteKey } from "./types";

export type RouteState = {
  organizationPublicId: string | null;
  route: RouteKey;
  employeeId: number | null;
  productCode: string | null;
  agentId: number | null;
  knowledgeId: number | null;
  clientId: number | null;
  channelId: number | null;
  supportPortalId: number | null;
};

export function routeFromPath(pathname: string, search = ""): RouteState {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const match = normalized.match(/^\/organizations\/([0-9a-f-]{36})(\/.*)?$/i);
  const organizationPublicId = match?.[1] ?? null;
  const path = match ? match[2] || "/" : normalized;
  const base = { employeeId: null, productCode: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, supportPortalId: null };
  const state = { organizationPublicId, ...base };
  if (path === "/" || path === "/command") return { route: "command", ...state };
  if (path === "/departments/sales") return { route: "salesDialogs", ...state };
  if (path === "/departments/support") return { route: "supportOverview", ...state };
  if (path === "/departments/support/dialogs") return { route: "supportDialogs", ...state };
  if (path === "/departments/sales/clients") return { route: "salesClients", ...state };
  if (path.startsWith("/departments/sales/clients/")) {
    const id = Number(path.split("/")[4]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "salesClientDetail", clientId: id } : { route: "salesClients", ...state };
  }
  if (path === "/departments/sales/dialogs") return { route: "salesDialogs", ...state };
  if (path === "/employees") return { route: "employees", ...state };
  if (path.startsWith("/employees/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "employeeDetail", employeeId: id } : { route: "employees", ...state };
  }
  if (path === "/departments/support/portals") return { route: "supportPortals", ...state };
  if (path.startsWith("/departments/support/portals/")) {
    const id = Number(path.split("/")[4]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "supportPortalDetail", supportPortalId: id } : { route: "supportPortals", ...state };
  }
  // Устаревшие адреса каналов и AI-агентов ведут в объединённый раздел.
  if (path === "/agents" || path === "/channels" || path === "/ai" || path === "/ai/agents") {
    return { route: "agents", ...state };
  }
  if (path.startsWith("/agents/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "agentDetail", agentId: id } : { route: "agents", ...state };
  }
  if (path.startsWith("/channels/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "agentDetail", agentId: id } : { route: "agents", ...state };
  }
  if (path.startsWith("/ai/agents/")) return { route: "agents", ...state };
  if (path === "/ai/knowledge") return { route: "aiKnowledge", ...state };
  if (path === "/ai/knowledge/new") return { route: "aiKnowledgeCreate", ...state };
  if (path.startsWith("/ai/knowledge/")) {
    const id = Number(path.split("/")[3]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "aiKnowledgeDetail", knowledgeId: id } : { route: "aiKnowledge", ...state };
  }
  if (path === "/ai/usage") return { route: "aiUsage", ...state };
  if (path === "/integrations") return { route: "integrations", ...state };
  if (path === "/administration" || path === "/administration/organization") {
    return { route: "administrationOrganization", ...state };
  }
  if (path === "/administration/subscription") {
    return { route: "administrationSubscription", ...state };
  }
  if (path === "/administration/audit") {
    return { route: "administrationAudit", ...state };
  }
  if (path === "/profile") return { route: "profile", ...state };
  if (path === "/settings") return { route: "settings", ...state };
  return { route: "command", ...state };
}

export function pathFromRoute(route: RouteKey, entityId: number | null = null, productCode: string | null = null, organizationPublicId: string | null = null): string {
  const prefix = organizationPublicId ? `/organizations/${organizationPublicId}` : "";
  if (route === "command") return `${prefix}/`;
  if (route === "supportOverview") return `${prefix}/departments/support`;
  if (route === "supportDialogs") return `${prefix}/departments/support/dialogs`;
  if (route === "salesClients") return `${prefix}/departments/sales/clients`;
  if (route === "salesClientDetail") return entityId ? `${prefix}/departments/sales/clients/${entityId}` : `${prefix}/departments/sales/clients`;
  if (route === "salesDialogs") return `${prefix}/departments/sales/dialogs`;
  if (route === "employees") return `${prefix}/employees`;
  if (route === "employeeDetail") return entityId ? `${prefix}/employees/${entityId}` : `${prefix}/employees`;
  if (route === "supportPortals") return `${prefix}/departments/support/portals`;
  if (route === "supportPortalDetail") return entityId ? `${prefix}/departments/support/portals/${entityId}` : `${prefix}/departments/support/portals`;
  if (route === "agents") return `${prefix}/agents`;
  if (route === "agentDetail") return entityId ? `${prefix}/agents/${entityId}` : `${prefix}/agents`;
  if (route === "aiUsage") return `${prefix}/ai/usage`;
  if (route === "aiKnowledge") return `${prefix}/ai/knowledge`;
  if (route === "aiKnowledgeCreate") return `${prefix}/ai/knowledge/new`;
  if (route === "aiKnowledgeDetail") return entityId ? `${prefix}/ai/knowledge/${entityId}` : `${prefix}/ai/knowledge`;
  if (route === "integrations") return `${prefix}/integrations`;
  if (route === "administrationOrganization") return `${prefix}/administration/organization`;
  if (route === "administrationSubscription") return `${prefix}/administration/subscription`;
  if (route === "administrationAudit") return `${prefix}/administration/audit`;
  if (route === "profile") return `${prefix}/profile`;
  if (route === "settings") return `${prefix}/settings`;
  return `${prefix}/profile`;
}
