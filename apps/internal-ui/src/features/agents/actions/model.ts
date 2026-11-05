import { api } from "../../../api/client";

export type ActionMode = "off" | "self" | "ask";
export type AgentAction = { id: string; title: string; subtitle: string; mode: ActionMode; revision: number; available: boolean; writes: boolean };
export const changedActions = (rows: readonly AgentAction[], saved: readonly AgentAction[]) => {
  const modes = new Map(saved.map(row => [row.id, row.mode]));
  return rows.filter(row => row.mode !== modes.get(row.id));
};
const base = (agent: number) => `/api/v1/integrations/agent-actions/${agent}/`;
export const loadActions = (agent: number, signal?: AbortSignal) => api<{ items: AgentAction[] }>(base(agent), { signal }).then(r => r.items);
export const saveActions = (agent: number, actions: AgentAction[]) => api<{ items: AgentAction[] }>(base(agent), {
  method: "PUT", body: JSON.stringify({ items: actions.map(({ id, mode, revision }) => ({ id, mode, revision })) }),
}).then(r => r.items);
