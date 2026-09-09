import type { RouteKey } from "./types";
import { t } from "./i18n";

export const routes: Record<RouteKey, string> = {
  administrationAudit: t("common.audit"),
  employeeDetail: t("common.operators"),
  employees: t("common.operators"),
  profile: t("common.profile"),
  settings: t("common.settings"),
  salesClientDetail: t("common.contact"),
  salesClients: t("common.contacts"),
  chat: t("common.chat"),
  supportPortals: t("common.portals"),
  supportPortalDetail: t("shared.support_portal"),
  supportPortalSettings: t("shared.portal_settings"),
  agents: t("common.agents"),
  agentDetail: t("shared.agent_card"),
  knowledge: t("common.knowledge_base"),
  knowledgeDetail: t("shared.knowledge_item"),
  knowledgeCreate: t("shared.new_knowledge_item"),
  knowledgeEdit: t("shared.knowledge_editor"),
  knowledgeCategories: t("shared.knowledge_categories"),
  knowledgeImport: t("shared.knowledge_import"),
  aiUsage: t("shared.ai_usage"),
};
