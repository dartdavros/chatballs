import { settingsSectionKey, type SettingsSectionKey } from "./features/settings/sections";
import {
  DEFAULT_PORTAL_SETTINGS_SECTION,
  portalSettingsSectionKey,
  type PortalSettingsSectionKey,
} from "./features/support-portals/sections";
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
  portalSettingsSection: PortalSettingsSectionKey | null;
  settingsSection: SettingsSectionKey | null;
};

export function routeFromPath(pathname: string, search = ""): RouteState {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const match = normalized.match(/^\/organizations\/([0-9a-f-]{36})(\/.*)?$/i);
  const organizationPublicId = match?.[1] ?? null;
  const path = match ? match[2] || "/" : normalized;
  const base = { employeeId: null, productCode: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, supportPortalId: null, portalSettingsSection: null, settingsSection: null };
  const state = { organizationPublicId, ...base };
  // Chat-first (SPEC-HUB-0031): корень и устаревшие адреса командного центра и
  // разделённых чатов ведут в единый «Чат».
  if (path === "/" || path === "/command" || path === "/chat" || path === "/departments/sales" || path === "/departments/sales/dialogs" || path === "/departments/support/dialogs") {
    return { route: "chat", ...state };
  }
  // Устаревший «Обзор поддержки» ведёт на «Доску».
  if (path === "/departments/support") return { route: "supportPortals", ...state };
  if (path === "/contacts" || path === "/departments/sales/clients") return { route: "salesClients", ...state };
  if (path.startsWith("/contacts/")) {
    const id = Number(path.slice("/contacts/".length));
    return Number.isInteger(id) && id > 0 ? { ...state, route: "salesClientDetail", clientId: id } : { route: "salesClients", ...state };
  }
  if (path.startsWith("/departments/sales/clients/")) {
    const id = Number(path.split("/")[4]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "salesClientDetail", clientId: id } : { route: "salesClients", ...state };
  }
  if (path === "/employees") return { route: "employees", ...state };
  if (path.startsWith("/employees/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { ...state, route: "employeeDetail", employeeId: id } : { route: "employees", ...state };
  }
  if (path === "/portals" || path === "/departments/support/portals") return { route: "supportPortals", ...state };
  if (path.startsWith("/portals/")) {
    const [, , rawId, subPath, subSection] = path.split("/");
    const id = Number(rawId);
    if (!Number.isInteger(id) || id <= 0) return { route: "supportPortals", ...state };
    // Настройки портала — страница с субменю разделов, а не модалка.
    if (subPath === "settings") {
      return {
        ...state,
        route: "supportPortalSettings",
        supportPortalId: id,
        portalSettingsSection: portalSettingsSectionKey(subSection ?? "") ?? DEFAULT_PORTAL_SETTINGS_SECTION,
      };
    }
    return { ...state, route: "supportPortalDetail", supportPortalId: id };
  }
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
  // Устаревшие адреса: интеграции и организация переехали в «Настройки» (§8.6).
  if (path === "/integrations") return { ...state, route: "settings", settingsSection: "integrations" };
  // /administration/subscription — устаревший адрес тарифов (ADR-HUB-0042).
  if (path === "/administration" || path === "/administration/organization" || path === "/administration/subscription") {
    return { ...state, route: "settings", settingsSection: "organization" };
  }
  if (path === "/administration/audit") {
    return { route: "administrationAudit", ...state };
  }
  if (path === "/profile") return { route: "profile", ...state };
  if (path === "/settings") return { route: "settings", ...state };
  if (path.startsWith("/settings/")) {
    return { ...state, route: "settings", settingsSection: settingsSectionKey(path.slice("/settings/".length)) };
  }
  return { route: "chat", ...state };
}

export function pathFromRoute(route: RouteKey, entityId: number | string | null = null, productCode: string | null = null, organizationPublicId: string | null = null): string {
  const prefix = organizationPublicId ? `/organizations/${organizationPublicId}` : "";
  if (route === "salesClients") return `${prefix}/contacts`;
  if (route === "salesClientDetail") return entityId ? `${prefix}/contacts/${entityId}` : `${prefix}/contacts`;
  if (route === "chat") return `${prefix}/chat`;
  if (route === "employees") return `${prefix}/employees`;
  if (route === "employeeDetail") return entityId ? `${prefix}/employees/${entityId}` : `${prefix}/employees`;
  if (route === "supportPortals") return `${prefix}/portals`;
  if (route === "supportPortalDetail") return entityId ? `${prefix}/portals/${entityId}` : `${prefix}/portals`;
  // У настроек портала в адресе и id портала, и ключ раздела: «12/basics».
  if (route === "supportPortalSettings") {
    const [portalId, section] = String(entityId ?? "").split("/");
    if (!portalId) return `${prefix}/portals`;
    return `${prefix}/portals/${portalId}/settings/${portalSettingsSectionKey(section ?? "") ?? DEFAULT_PORTAL_SETTINGS_SECTION}`;
  }
  if (route === "agents") return `${prefix}/agents`;
  if (route === "agentDetail") return entityId ? `${prefix}/agents/${entityId}` : `${prefix}/agents`;
  if (route === "aiUsage") return `${prefix}/ai/usage`;
  if (route === "aiKnowledge") return `${prefix}/ai/knowledge`;
  if (route === "aiKnowledgeCreate") return `${prefix}/ai/knowledge/new`;
  if (route === "aiKnowledgeDetail") return entityId ? `${prefix}/ai/knowledge/${entityId}` : `${prefix}/ai/knowledge`;
  if (route === "administrationAudit") return `${prefix}/administration/audit`;
  if (route === "profile") return `${prefix}/profile`;
  // У «Настроек» вместо id — ключ раздела субменю (кадры N1–N7).
  if (route === "settings") return settingsSectionKey(String(entityId)) ? `${prefix}/settings/${entityId}` : `${prefix}/settings`;
  return `${prefix}/profile`;
}
