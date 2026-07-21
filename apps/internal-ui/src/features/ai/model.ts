export type ChannelRef = {
  id: number;
  code: string;
  name: string;
  department: { id: number; code: string; name: string } | null;
  product: { code: string; name: string } | null;
};

export type AgentKnowledgeRef = { id: number; title: string; isEnabled: boolean };

export type CredentialMode = "CUSTOAI" | "BYOK";

export const CREDENTIAL_MODE_OPTIONS: Array<[CredentialMode, string]> = [
  ["CUSTOAI", "CustoAI (Managed)"],
  ["BYOK", "BYOK"],
];

export type AiAgent = {
  id: number;
  channel: ChannelRef;
  name: string;
  isActive: boolean;
  model: string;
  credentialMode: CredentialMode;
  // BYOK-провайдер принадлежит агенту, а не каналу (SPEC-HUB-0027 §9).
  providerIntegrationId: number | null;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
  persona: string;
  tone: string;
  instructions: string;
  knowledge: AgentKnowledgeRef[];
};
