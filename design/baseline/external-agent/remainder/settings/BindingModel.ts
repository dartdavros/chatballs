export type BindingAgent = [string, string];
export type AgentBinding = { id: number; agentId: string; externalId: string };
export type BindingDraft = Pick<AgentBinding, 'agentId' | 'externalId'>;
export type BindingPatch = Partial<BindingDraft>;

export function availableBindingAgents(agents: BindingAgent[], bindings: AgentBinding[], exceptId?: number) {
  return agents.filter(([id]) => !bindings.some(binding => binding.id !== exceptId && binding.agentId === id));
}

export function normalizedBindingDraft(draft: BindingDraft, agents: BindingAgent[]): BindingDraft | null {
  const externalId = draft.externalId.trim();
  return externalId && agents.some(([id]) => id === draft.agentId) ? { agentId: draft.agentId, externalId } : null;
}
