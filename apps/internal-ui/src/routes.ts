import type { RouteKey } from "./types";
import { t, type MessageKey } from "./i18n";

const routeTitleKeys: Record<RouteKey, MessageKey> = {
  ruleJournal: "handling_rules.journal_title",
  qualityAnalysis: "quality.title",
  supportReports: "reports.title",
  replyTemplates: "settings.reply_templates",
  administrationAudit: "common.audit",
  employeeDetail: "common.operators",
  employees: "common.operators",
  profile: "common.profile",
  settings: "common.settings",
  aiProviders: "navigation.ai_providers",
  scenarios: "scenarios.title",
  widgets: "navigation.widgets",
  messengers: "navigation.messengers",
  emailIntegrations: "navigation.mail",
  webIntegrationSettings: "navigation.widgets",
  externalServerSettings: "navigation.tools",
  legacyIntegrationSettings: "common.integrations",
  integrationServers: "navigation.tools",
  serviceIntegrations: "common.integrations",
  serviceConnection: "common.integrations",
  mcpServerCreate: "servers.new_mcp",
  httpServerCreate: "servers.new_http",
  salesClientDetail: "common.contact",
  salesClients: "common.contacts",
  chat: "page_titles.chats",
  supportPortals: "common.portals",
  supportPortalDetail: "shared.support_portal",
  supportPortalSettings: "shared.portal_settings",
  skills: "skills.title",
  agents: "common.agents",
  agentDetail: "shared.agent_card",
  knowledge: "common.knowledge_base",
  knowledgeDetail: "shared.knowledge_item",
  knowledgeCreate: "shared.new_knowledge_item",
  knowledgeEdit: "shared.knowledge_editor",
  knowledgeCategories: "shared.knowledge_categories",
  knowledgeImport: "shared.knowledge_import",
  aiUsage: "shared.ai_usage",
  organizationCreate: "organizations.create_title",
};

/** Названия вычисляются на текущем языке, в том числе после смены языка. */
export function routeTitle(route: RouteKey): string {
  return t(routeTitleKeys[route]);
}

export const routes = Object.fromEntries(
  Object.keys(routeTitleKeys).map(key => [key, routeTitle(key as RouteKey)]),
) as Record<RouteKey, string>;
