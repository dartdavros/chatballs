import { useIntegrations } from "../settings/useIntegrations";
import { WebIntegrationPage } from "./WebIntegrationPage";
import { ExternalServerPage } from "./external/ExternalServerPage";
import type { ServerKind } from "./external/types";
import { ServerPageLoading } from "./external/ServerPageLoading";
import { ServerPageState } from "./external/ServerPageState";

export function IntegrationSettingsPage({ integrationId, createKind, expectedKind, onCreated, onBack }: {
  integrationId?: number; createKind?: ServerKind; expectedKind?: "web" | "server";
  onCreated: (id: number) => void; onBack: () => void;
}) {
  const list = useIntegrations(true);
  const integration = list.items.find((i) => i.id === integrationId);
  if (list.loading) return <ServerPageLoading />;
  const mismatched = integration && (expectedKind === "web" ? integration.provider !== "WEB"
    : expectedKind === "server" && integration.kind !== "EXTERNAL_SERVER");
  if (list.failed || (!createKind && (!integration || mismatched))) return <ServerPageState kind={expectedKind}
    failed={list.failed} onRetry={list.reload} onBack={onBack} />;
  if (integration?.provider === "WEB") return <WebIntegrationPage integrationId={integration.id} onBack={onBack} />;
  if (createKind || integration?.externalServer) return <ExternalServerPage key={integration?.id ?? createKind} initial={integration ?? null}
    kind={createKind ?? integration!.externalServer!.type} integrations={list.items} onCreated={onCreated} onBack={onBack} />;
  return <ServerPageState kind={expectedKind} onRetry={list.reload} onBack={onBack} />;
}
