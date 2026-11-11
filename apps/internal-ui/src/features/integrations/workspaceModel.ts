import { t } from "../../i18n";
import type { Integration, IntegrationProvider } from "./model";

export type IntegrationWorkspaceMode = "providers" | "widgets" | "messengers" | "mail" | "servers";
export type ServerFilter = "all" | "MCP" | "HTTP";

export const WORKSPACE_PROVIDERS: Record<IntegrationWorkspaceMode, readonly IntegrationProvider[]> = {
  providers: ["OPENROUTER", "CUSTOM", "DEMO", "YANDEX_SPEECHKIT"],
  widgets: ["WEB"],
  messengers: ["TELEGRAM", "MAX", "VK"],
  mail: ["EMAIL"],
  servers: ["MCP", "HTTP"],
};

export function workspaceItems(items: Integration[], mode: IntegrationWorkspaceMode, filter: ServerFilter = "all") {
  const allowed = WORKSPACE_PROVIDERS[mode];
  return items.filter(item => allowed.includes(item.provider)
    && (mode !== "servers" || filter === "all" || item.provider === filter));
}

export function workspaceLabels(mode: IntegrationWorkspaceMode) {
  const labels = {
    providers: { title: t("navigation.ai_providers"), lead: t("navigation.providers_lead"),
      add: t("settings.add_provider"), edit: t("navigation.edit_provider"), empty: t("navigation.providers_empty") },
    widgets: { title: t("navigation.widgets"), lead: t("navigation.widgets_lead"),
      add: t("navigation.add_widget"), edit: t("navigation.edit_widget"), empty: t("navigation.widgets_empty") },
    messengers: { title: t("navigation.messengers"), lead: t("navigation.messengers_lead"),
      add: t("navigation.connect_messenger"), edit: t("navigation.edit_messenger"), empty: t("navigation.messengers_empty") },
    mail: { title: t("navigation.mail"), lead: t("navigation.mail_lead"),
      add: t("navigation.connect_mail"), edit: t("navigation.edit_mail"), empty: t("navigation.mail_empty") },
    servers: { title: t("navigation.tools"), lead: t("navigation.tools_lead"),
      add: t("navigation.add_tool"), edit: t("common.edit"), empty: t("navigation.tools_empty") },
  };
  return labels[mode];
}
