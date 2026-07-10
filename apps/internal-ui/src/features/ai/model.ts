export type ChannelRef = { id: number; code: string; name: string; product: { code: string; name: string } | null };

export type AgentKnowledgeRef = { id: number; title: string; isEnabled: boolean };

export type AiAgent = {
  id: number;
  channel: ChannelRef;
  name: string;
  isActive: boolean;
  model: string;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
  persona: string;
  tone: string;
  instructions: string;
  knowledge: AgentKnowledgeRef[];
};
