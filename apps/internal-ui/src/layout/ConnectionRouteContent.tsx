import { IntegrationSettingsPage } from "../features/integrations/IntegrationSettingsPage";
import { IntegrationWorkspacePage } from "../features/integrations/IntegrationWorkspacePage";
import { IntegrationWorkspaceLayout } from "../features/integrations/IntegrationWorkspaceLayout";
import { ServicesPage } from "../features/integrations/services/ServicesPage";
import { ScenariosWorkspace } from "../features/integrations/scenarios/ScenariosWorkspace";
import type { RouteKey, SessionUser } from "../types";
import { LegacyIntegrationRoute } from "./LegacyIntegrationRoute";

const WORKSPACES = {
  aiProviders: "providers",
  widgets: "widgets",
  messengers: "messengers",
  emailIntegrations: "mail",
  integrationServers: "servers",
} as const;

export function isConnectionWorkspace(route: RouteKey): boolean {
  return route in WORKSPACES || ["scenarios", "webIntegrationSettings", "externalServerSettings",
    "legacyIntegrationSettings", "mcpServerCreate", "httpServerCreate", "serviceIntegrations", "serviceConnection"].includes(route);
}

export function ConnectionRouteContent({ route, integrationId, user, setRoute, openWidget, openServer,
  openService, openScenario, resolveLegacy }: {
  route: RouteKey;
  integrationId: number | null;
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  openWidget: (id: number) => void;
  openServer: (id: number) => void;
  openService: (id: number) => void;
  openScenario: (id: string) => void;
  resolveLegacy: (route: RouteKey, id: number | null) => void;
}) {
  if (route in WORKSPACES) return <IntegrationWorkspacePage
    key={`${user.organizationPublicId}:${route}`} mode={WORKSPACES[route as keyof typeof WORKSPACES]} user={user}
    openWebIntegration={openWidget} openServer={openServer}
    createServer={(kind) => setRoute(kind === "mcp" ? "mcpServerCreate" : "httpServerCreate")} />;
  if (route === "scenarios") return <IntegrationWorkspaceLayout><ScenariosWorkspace /></IntegrationWorkspaceLayout>;
  if (route === "serviceIntegrations" || route === "serviceConnection") return <ServicesPage
    key={`${user.organizationPublicId}:${integrationId ?? "list"}`} user={user}
    connectionId={route === "serviceConnection" ? integrationId ?? undefined : undefined}
    openConnection={openService} openScenario={openScenario} onBack={() => setRoute("serviceIntegrations")} />;
  if (route === "legacyIntegrationSettings" && integrationId !== null) return <LegacyIntegrationRoute
    id={integrationId} onResolved={resolveLegacy} onBack={() => setRoute("widgets")} />;
  if (route === "webIntegrationSettings" && integrationId !== null) return <IntegrationSettingsPage
    key={integrationId} integrationId={integrationId} expectedKind="web"
    onCreated={openWidget} onBack={() => setRoute("widgets")} />;
  if (route === "externalServerSettings" && integrationId !== null) return <IntegrationSettingsPage
    key={integrationId} integrationId={integrationId} expectedKind="server"
    onCreated={openServer} onBack={() => setRoute("integrationServers")} />;
  if (route === "mcpServerCreate" || route === "httpServerCreate") return <IntegrationSettingsPage
    key={route} createKind={route === "mcpServerCreate" ? "mcp" : "http"}
    onCreated={openServer} onBack={() => setRoute("integrationServers")} />;
  return null;
}
