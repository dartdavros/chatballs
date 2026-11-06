import { api } from "../../../api/client";
import { fetchAdapters, fetchConnections } from "../services/api";
import type { EditorCatalog, ExchangeSettings, ExternalKey, Issue, Scenario, ScenarioDocument } from "./types";

const BASE = "/api/v1/integrations/scenarios/";
export async function fetchCatalog(): Promise<EditorCatalog> {
  const [catalog, adapters, connections] = await Promise.all([
    api<Omit<EditorCatalog, "adapters" | "connections">>(`${BASE}catalog/`), fetchAdapters(), fetchConnections(),
  ]);
  return { ...catalog, adapters, connections };
}
export const listScenarios = (connection?: number) => api<{ items: Scenario[] }>(`${BASE}${connection ? `?connection=${connection}` : ""}`).then(r => r.items);
export const fetchScenario = (id: string) => api<{ scenario: Scenario }>(`${BASE}${id}/`).then(r => r.scenario);
export const saveScenario = (scenario: Pick<Scenario, "name" | "definition" | "enabled" | "agentPolicies"> & { id?: string; revision?: number }) => {
  const { id, ...body } = scenario;
  return api<{ scenario: Scenario }>(`${BASE}${id ? `${id}/` : ""}`, { method: id ? "PUT" : "POST", body: JSON.stringify(body) }).then(r => r.scenario);
};
export const checkScenario = (definition: ScenarioDocument, signal?: AbortSignal) => api<{ valid: boolean; issues: Issue[] }>(`${BASE}check/`, { method: "POST", body: JSON.stringify({ definition }), signal });
export const copyScenario = (id: string, name: string) => api<{ scenario: Scenario }>(`${BASE}${id}/copy/`, { method: "POST", body: JSON.stringify({ name }) }).then(r => r.scenario);
export const deleteScenario = (id: string, revision: number) => api(`${BASE}${id}/`, { method: "DELETE", body: JSON.stringify({ revision }) });
export const copyPreset = (connection: number, key: string) => api<{ scenario: Scenario }>(`/api/v1/integrations/services/${connection}/presets/${key}/`, { method: "POST", body: "{}" }).then(r => r.scenario);
export const rotateExternalKey = (id: string, trigger: string, revision: number) => api<{ externalKey: ExternalKey }>(`${BASE}${id}/keys/${trigger}/rotate/`, { method: "POST", body: JSON.stringify({ revision }) }).then(r => r.externalKey);
export const fetchExchange = (connection: number) => api<ExchangeSettings>(`/api/v1/integrations/services/${connection}/synchronization/`);
export const saveExchange = (connection: number, settings: ExchangeSettings) => api<ExchangeSettings>(`/api/v1/integrations/services/${connection}/synchronization/`, { method: "PUT", body: JSON.stringify(settings) });
