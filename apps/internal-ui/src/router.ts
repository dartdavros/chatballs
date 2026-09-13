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
  // Страница создания организации живёт вне организации: у неё ещё нет
  // адреса, а человек попадает сюда из переключателя любой из своих (A1).
  if (normalized === "/organizations/new") {
    return { route: "organizationCreate", organizationPublicId: null, employeeId: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, supportPortalId: null, portalSettingsSection: null, settingsSection: null };
  }
  const match = normalized.match(/^\/organizations\/([0-9a-f-]{36})(\/.*)?$/i);
  const organizationPublicId = match?.[1] ?? null;
  const path = match ? match[2] || "/" : normalized;
  const base = { employeeId: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, supportPortalId: null, portalSettingsSection: null, settingsSection: null };
  const state = { organizationPublicId, ...base };
  // Chat-first (SPEC-CHATBALLS-0031): корень и устаревшие адреса командного центра и
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
  // «База знаний» — самостоятельный раздел сайдбара, а не ссылка из «Настроек»
  // (дизайн-базлайн v2, кадры KB1–KB9). Старые адреса /ai/knowledge ведут сюда.
  if (path === "/knowledge" || path === "/ai/knowledge") return { route: "knowledge", ...state };
  if (path === "/knowledge/new" || path === "/ai/knowledge/new") return { route: "knowledgeCreate", ...state };
  if (path === "/knowledge/categories") return { route: "knowledgeCategories", ...state };
  if (path === "/knowledge/import") return { route: "knowledgeImport", ...state };
  if (path.startsWith("/knowledge/") || path.startsWith("/ai/knowledge/")) {
    const parts = path.split("/");
    const legacy = parts[1] === "ai";
    const id = Number(parts[legacy ? 3 : 2]);
    if (!Number.isInteger(id) || id <= 0) return { route: "knowledge", ...state };
    const tail = parts[legacy ? 4 : 3];
    return { ...state, route: tail === "edit" ? "knowledgeEdit" : "knowledgeDetail", knowledgeId: id };
  }
  if (path === "/ai/usage") return { route: "aiUsage", ...state };
  // Устаревшие адреса: интеграции и организация переехали в «Настройки» (§8.6).
  if (path === "/integrations") return { ...state, route: "settings", settingsSection: "integrations" };
  // /administration/subscription — устаревший адрес тарифов (ADR-CHATBALLS-0042).
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

export function pathFromRoute(route: RouteKey, entityId: number | string | null = null, organizationPublicId: string | null = null): string {
  const prefix = organizationPublicId ? `/organizations/${organizationPublicId}` : "";
  if (route === "organizationCreate") return "/organizations/new";
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
  if (route === "knowledge") return `${prefix}/knowledge`;
  if (route === "knowledgeCreate") return `${prefix}/knowledge/new`;
  if (route === "knowledgeCategories") return `${prefix}/knowledge/categories`;
  if (route === "knowledgeImport") return `${prefix}/knowledge/import`;
  if (route === "knowledgeDetail") return entityId ? `${prefix}/knowledge/${entityId}` : `${prefix}/knowledge`;
  if (route === "knowledgeEdit") return entityId ? `${prefix}/knowledge/${entityId}/edit` : `${prefix}/knowledge/new`;
  if (route === "administrationAudit") return `${prefix}/administration/audit`;
  if (route === "profile") return `${prefix}/profile`;
  // У «Настроек» вместо id — ключ раздела субменю (кадры N1–N7).
  if (route === "settings") return settingsSectionKey(String(entityId)) ? `${prefix}/settings/${entityId}` : `${prefix}/settings`;
  return `${prefix}/profile`;
}
