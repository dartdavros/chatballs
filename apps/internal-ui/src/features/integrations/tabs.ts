import { t } from "../../i18n";
import type { RouteKey } from "../../types";

// Вкладки раздела «Интеграции» (Сервисы.dc.html): точки входа диалогов,
// внешние серверы и сервисы. У каждой — свой адрес, у подключения сервиса — карточка.
export type IntegrationsTab = "entry" | "servers" | "services";
export type IntegrationsView = { tab: IntegrationsTab; serviceId?: number };

export const INTEGRATIONS_TABS: Array<{ key: IntegrationsTab; label: string }> = [
  { key: "entry", label: t("services.tab_entry") },
  { key: "servers", label: t("services.tab_servers") },
  { key: "services", label: t("services.tab_services") },
];

export const TAB_ROUTE: Record<Exclude<IntegrationsTab, "entry">, RouteKey> = {
  servers: "integrationServers",
  services: "serviceIntegrations",
};

export function isIntegrationsRoute(route: RouteKey): boolean {
  return route === "integrationServers" || route === "serviceIntegrations" || route === "serviceConnection";
}

export function integrationsView(route: RouteKey, integrationId: number | null): IntegrationsView | undefined {
  if (route === "integrationServers") return { tab: "servers" };
  if (route === "serviceIntegrations") return { tab: "services" };
  if (route === "serviceConnection" && integrationId) return { tab: "services", serviceId: integrationId };
  return undefined;
}
