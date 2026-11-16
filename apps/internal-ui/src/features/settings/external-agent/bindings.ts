import type { ConnectionDraft, ExternalBinding, ExternalConnection, SettingsCatalog } from "./model";

export function emptyBinding(agent: SettingsCatalog["agents"][number], externalAgentId: string): ExternalBinding {
  return { agentId: agent.id, channelId: agent.channelId, agentName: agent.name, externalAgentId: externalAgentId.trim(),
    enabled: true, revision: 0, policyVersion: 0, policyAccepted: false,
    standardFields: [], customFields: [], templateIds: [], proactiveEnabled: false,
    processingMode: "ordinary", ordinaryTimeout: 120, longTimeout: 86400, maximumTimeout: 86400 };
}

export function configurationChanges(previous: ExternalConnection, draft: ConnectionDraft) {
  const connection: Record<string, unknown> = {};
  for (const key of ["name", "baseUrl", "enabled"] as const) {
    if (previous[key] !== draft[key]) connection[key] = draft[key];
  }
  if (draft.outboundKey) connection.outboundKey = draft.outboundKey;
  const bindings = draft.bindings.filter(binding => JSON.stringify(binding) !== JSON.stringify(
    previous.bindings.find(item => item.agentId === binding.agentId),
  )).map(({ agentId, externalAgentId, policyAccepted, standardFields, customFields, templateIds, proactiveEnabled,
    processingMode, ordinaryTimeout, longTimeout, maximumTimeout }) => ({ agentId, externalAgentId, policyAccepted,
    standardFields, customFields, templateIds, proactiveEnabled, processingMode, ordinaryTimeout, longTimeout, maximumTimeout }));
  return { revision: previous.revision, bindingRevisions: Object.fromEntries(previous.bindings.map(binding =>
    [String(binding.agentId), [binding.revision, binding.policyVersion]])), connection, bindings,
    removeAgentIds: previous.bindings.filter(binding => !draft.bindings.some(item => item.agentId === binding.agentId)).map(binding => binding.agentId) };
}
