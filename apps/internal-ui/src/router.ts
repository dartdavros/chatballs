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
  integrationId: number | null;
  supportPortalId: number | null;
  portalSettingsSection: PortalSettingsSectionKey | null;
  settingsSection: SettingsSectionKey | null;
  conversationId?: number | null;
};

export function routeFromPath(pathname: string, search = ""): RouteState {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  // Страница создания организации живёт вне организации: у неё ещё нет
  // адреса, а человек попадает сюда из переключателя любой из своих (A1).
  if (normalized === "/organizations/new") {
    return { route: "organizationCreate", organizationPublicId: null, employeeId: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, integrationId: null, supportPortalId: null, portalSettingsSection: null, settingsSection: null };
  }
  const match = normalized.match(/^\/organizations\/([0-9a-f-]{36})(\/.*)?$/i);
  const organizationPublicId = match?.[1] ?? null;
  const path = match ? match[2] || "/" : normalized;
  const base = { employeeId: null, agentId: null, knowledgeId: null, clientId: null, channelId: null, integrationId: null, supportPortalId: null, portalSettingsSection: null, settingsSection: null };
  const state = { organizationPublicId, ...base };
  const qualityMatch = path.match(/^\/conversations\/(\d+)\/quality$/);
  if (qualityMatch && Number(qualityMatch[1]) > 0) return { ...state, route: "qualityAnalysis", conversationId: Number(qualityMatch[1]) };
  if (path === "/statistics") return { ...state, route: "supportReports" };
  if (path === "/settings/rules/journal") return { ...state, route: "ruleJournal" };
  if (path === "/reply-templates") return { ...state, route: "replyTemplates" };
  // Chat-first (SPEC-CHATBALLS-0031): корень и устаревшие адреса командного центра и
  // разделённых чатов ведут в единый «Чат».
  if (path === "/" || path === "/command" || path === "/chat" || path === "/departments/sales" || path === "/departments/sales/dialogs" || path === "/departments/support/dialogs") {
    const conversationId = Number(new URLSearchParams(search).get("conversation"));
    return { route: "chat", ...state, ...(Number.isSafeInteger(conversationId) && conversationId > 0 ? { conversationId } : {}) };
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
  if (path === "/agents/skills") return { route: "skills", ...state };
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
  // /administration/subscription — устаревший адрес тарифов (ADR-CHATBALLS-0042).
  if (path === "/administration" || path === "/administration/organization" || path === "/administration/subscription") {
    return { ...state, route: "settings", settingsSection: "organization" };
  }
  if (path === "/administration/audit") {
    return { route: "administrationAudit", ...state };
  }
  if (path === "/profile") return { route: "profile", ...state };
  if (path === "/settings") return { route: "settings", ...state };

  // Самостоятельные разделы и их прежние адреса внутри «Настроек».
  const workspaceRoutes: Partial<Record<string, RouteKey>> = {
    "/ai/providers": "aiProviders", "/settings/ai": "aiProviders",
    "/scenarios": "scenarios", "/settings/scenarios": "scenarios",
    "/widgets": "widgets", "/settings/integrations": "widgets",
    "/messengers": "messengers", "/mail": "emailIntegrations",
    "/tools": "integrationServers", "/settings/integrations/servers": "integrationServers",
    "/tools/new/mcp": "mcpServerCreate", "/settings/integrations/new/mcp": "mcpServerCreate",
    "/tools/new/http": "httpServerCreate", "/settings/integrations/new/http": "httpServerCreate",
    "/integrations": "serviceIntegrations", "/settings/integrations/services": "serviceIntegrations",
  };
  const workspaceRoute = workspaceRoutes[path];
  if (workspaceRoute) return { ...state, route: workspaceRoute };
  const integrationPaths: [string, RouteKey, RouteKey][] = [
    ["/widgets/", "webIntegrationSettings", "widgets"],
    ["/tools/", "externalServerSettings", "integrationServers"],
    ["/integrations/", "serviceConnection", "serviceIntegrations"],
    ["/settings/integrations/services/", "serviceConnection", "serviceIntegrations"],
    // Тип старого подключения определяет API, а не форма прежнего URL.
    ["/settings/integrations/", "legacyIntegrationSettings", "widgets"],
  ];
  for (const [prefix, detailRoute, listRoute] of integrationPaths) {
    if (!path.startsWith(prefix)) continue;
    const id = Number(path.slice(prefix.length));
    return Number.isSafeInteger(id) && id > 0
      ? { ...state, route: detailRoute, integrationId: id }
      : { ...state, route: listRoute };
  }
  if (path.startsWith("/settings/")) {
    return { ...state, route: "settings", settingsSection: settingsSectionKey(path.slice("/settings/".length)) };
  }
  return { route: "chat", ...state };
}

function routePath(route: RouteKey, entityId: number | string | null, organizationPublicId: string | null): string {
  const prefix = organizationPublicId ? `/organizations/${organizationPublicId}` : "";
  if (route === "organizationCreate") return "/organizations/new";
  if (route === "salesClients") return `${prefix}/contacts`;
  if (route === "salesClientDetail") return entityId ? `${prefix}/contacts/${entityId}` : `${prefix}/contacts`;
  if (route === "chat") return `${prefix}/chat${entityId ? `?conversation=${entityId}` : ""}`;
  if (route === "qualityAnalysis") return `${prefix}/conversations/${entityId}/quality`;
  if (route === "supportReports") return `${prefix}/statistics`;
  if (route === "ruleJournal") return `${prefix}/settings/rules/journal`;
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
  if (route === "skills") return `${prefix}/agents/skills`;
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
  if (route === "replyTemplates") return `${prefix}/reply-templates`;
  if (route === "aiProviders") return `${prefix}/ai/providers`;
  if (route === "scenarios") return `${prefix}/scenarios`;
  if (route === "widgets") return `${prefix}/widgets`;
  if (route === "messengers") return `${prefix}/messengers`;
  if (route === "emailIntegrations") return `${prefix}/mail`;
  if (route === "webIntegrationSettings") return entityId ? `${prefix}/widgets/${entityId}` : `${prefix}/widgets`;
  if (route === "externalServerSettings") return entityId ? `${prefix}/tools/${entityId}` : `${prefix}/tools`;
  if (route === "legacyIntegrationSettings") return entityId ? `${prefix}/settings/integrations/${entityId}` : `${prefix}/settings/integrations`;
  if (route === "mcpServerCreate") return `${prefix}/tools/new/mcp`;
  if (route === "integrationServers") return `${prefix}/tools`;
  if (route === "serviceIntegrations") return `${prefix}/integrations`;
  if (route === "serviceConnection") return entityId ? `${prefix}/integrations/${entityId}` : `${prefix}/integrations`;
  if (route === "httpServerCreate") return `${prefix}/tools/new/http`;
  // У «Настроек» вместо id — ключ раздела субменю (кадры N1–N7).
  if (route === "settings") return settingsSectionKey(String(entityId)) ? `${prefix}/settings/${entityId}` : `${prefix}/settings`;
  return `${prefix}/profile`;
}

export function pathFromRoute(route: RouteKey, entityId: number | string | null = null, organizationPublicId: string | null = null, search = ""): string {
  const path = routePath(route, entityId, organizationPublicId);
  if (!search) return path;
  const [pathname, routeSearch] = path.split("?");
  const params = new URLSearchParams(search);
  // ID диалога из состояния важнее старого query при смене организации/адреса.
  new URLSearchParams(routeSearch).forEach((value, key) => params.set(key, value));
  const query = params.toString();
  return `${pathname}${query ? `?${query}` : ""}`;
}

/** Канонический адрес сохраняет выбранную сущность, раздел портала и query. */
export function pathFromRouteState(state: RouteState, organizationPublicId: string | null = state.organizationPublicId, search = ""): string {
  const entityIds: Partial<Record<RouteKey, number | string | null | undefined>> = {
    chat: state.conversationId,
    qualityAnalysis: state.conversationId,
    employeeDetail: state.employeeId,
    agentDetail: state.agentId ?? state.channelId,
    knowledgeDetail: state.knowledgeId,
    knowledgeEdit: state.knowledgeId,
    salesClientDetail: state.clientId,
    webIntegrationSettings: state.integrationId,
    externalServerSettings: state.integrationId,
    legacyIntegrationSettings: state.integrationId,
    serviceConnection: state.integrationId,
    supportPortalDetail: state.supportPortalId,
    supportPortalSettings: state.supportPortalId ? `${state.supportPortalId}/${state.portalSettingsSection ?? ""}` : null,
    settings: state.settingsSection,
  };
  return pathFromRoute(state.route, entityIds[state.route] ?? null, organizationPublicId, search);
}
