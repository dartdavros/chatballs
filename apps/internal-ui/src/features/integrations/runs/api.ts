import { api } from "../../../api/client";
import type { ManualAction, RetentionPolicy, RunDetail, RunPage, ManualCatalog, PlanPreview } from "./types";

const BASE = "/api/v1/integrations/";
export const listRuns = (query: URLSearchParams) => api<RunPage>(`${BASE}runs/?${query}`);
export const getRun = (id: string) => api<{ run: RunDetail }>(`${BASE}runs/${id}/`).then(r => r.run);
export const controlRun = (id: string, action: string, body: object = {}) => api<{ run: RunDetail }>(`${BASE}runs/${id}/${action}/`, {
  method: "POST", body: JSON.stringify(body),
}).then(r => r.run);
export const getManualActions = (conversation: number) => api<ManualCatalog>(`${BASE}run-actions/?conversation=${conversation}`);
export const launchBody = (action: ManualAction, conversationId: number, parameters: Record<string, unknown>, triggerKey: string) => ({
  kind: action.kind, scenarioId: action.kind === "scenario" ? action.id : undefined, connectionId: action.connectionId,
  operationKey: action.operationKey, conversationId, parameters, triggerKey,
});
export const launchManual = (action: ManualAction, conversationId: number, parameters: Record<string, unknown>, triggerKey: string, confirmation: string) => api<{ run: RunDetail }>(`${BASE}run-actions/`, {
  method: "POST", body: JSON.stringify({ ...launchBody(action, conversationId, parameters, triggerKey), confirmation }),
}).then(r => r.run);
export const previewManual = (action: ManualAction, conversationId: number, parameters: Record<string, unknown>, triggerKey: string) => api<{ preview: PlanPreview }>(`${BASE}run-actions/`, {
  method: "POST", body: JSON.stringify({ ...launchBody(action, conversationId, parameters, triggerKey), preview: true }),
}).then(result => result.preview);
export const manualLookup = (action: ManualAction, conversationId: number, connection: string, lookup: string) => api<{ items: Array<{ value: string | number; label: string }> }>(
  `${BASE}run-actions/lookup/?${new URLSearchParams({ conversation: String(conversationId), connection, lookup,
    operation: action.operationKey ?? "", ...(action.kind === "scenario" ? { scenario: action.id } : {}) })}`).then(result => result.items);
export const getRetention = () => api<RetentionPolicy>(`${BASE}runs/retention/`);
export const saveRetention = (policy: RetentionPolicy, confirmed: boolean) => api<RetentionPolicy>(`${BASE}runs/retention/`, {
  method: "PUT", body: JSON.stringify({ ...policy, confirmed }),
});
