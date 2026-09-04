// Единая сущность «Агент» = канал + AI-конфигурация (ADR-HUB-0041 §4).
// Источник данных — агрегированный API /api/v1/agents/.
import { api } from "../../api/client";
import type { AgentKnowledgeRef, AgentPortalArticleRef, CredentialMode } from "../ai/model";

export type AgentConnection = {
  id: number;
  provider: string;
  name: string;
  status: string;
};

export type AgentAiStatus = "DRAFT" | "ACTIVE" | "DISABLED";

export type AgentCard = {
  id: number;
  aiAgentId: number;
  code: string;
  name: string;
  isActive: boolean;
  groupId: number | null;
  groupName: string | null;
  aiStatus: AgentAiStatus;
  model: string;
  credentialMode: CredentialMode;
  providerIntegrationId: number | null;
  modelParams: Record<string, unknown>;
  limits: Record<string, unknown>;
  persona: string;
  tone: string;
  instructions: string;
  knowledge: AgentKnowledgeRef[];
  portalArticles: AgentPortalArticleRef[];
  connections: AgentConnection[];
  counters: { openConversations: number; connections: number };
  createdAt: string;
  updatedAt: string;
};

export type AgentPatch = Partial<{
  name: string;
  groupId: number | null;
  isActive: boolean;
  credentialMode: CredentialMode;
  providerIntegrationId: number | null;
  persona: string;
  tone: string;
  instructions: string;
  knowledgeIds: number[];
  limits: Record<string, unknown>;
}>;

export function fetchAgents(): Promise<{ items: AgentCard[] }> {
  return api<{ items: AgentCard[] }>("/api/v1/agents/");
}

export function fetchAgent(agentId: number): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/`);
}

export function createAgent(input: { name: string; groupId: number | null }): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>("/api/v1/agents/", { method: "POST", body: JSON.stringify(input) });
}

export function patchAgent(agentId: number, patch: AgentPatch): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/`, { method: "PATCH", body: JSON.stringify(patch) });
}

export function deleteAgent(agentId: number): Promise<void> {
  return api<void>(`/api/v1/agents/${agentId}/`, { method: "DELETE" });
}

export function setAgentAiActive(agentId: number, active: boolean): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/${active ? "activate" : "deactivate"}/`, { method: "POST" });
}

export function bindAgentConnection(agentId: number, integrationId: number, force = false): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/connections/`, {
    method: "POST",
    body: JSON.stringify({ integrationId, force }),
  });
}

export function unbindAgentConnection(agentId: number, integrationId: number): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/connections/${integrationId}/`, { method: "DELETE" });
}

// Статус карточки для списка: канал выключен > AI активен > черновик.
export function agentStatusLabel(card: AgentCard): { text: string; tone: "active" | "paused" | "disabled" } {
  if (!card.isActive) return { text: "Выключен", tone: "disabled" };
  if (card.aiStatus === "ACTIVE") return { text: "AI отвечает", tone: "active" };
  return { text: "Без AI", tone: "paused" };
}
