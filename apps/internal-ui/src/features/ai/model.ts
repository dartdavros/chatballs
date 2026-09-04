export type ChannelRef = {
  id: number;
  code: string;
  name: string;
  group: { id: number; name: string } | null;
  product: { code: string; name: string } | null;
};

export type AgentKnowledgeRef = { id: number; title: string; isEnabled: boolean };

export type AgentPortalArticleRef = {
  id: number;
  title: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  portal: { id: number; name: string };
  publicUrl: string;
};

export type AiAgent = {
  id: number;
  channel: ChannelRef;
  name: string;
  isActive: boolean;
  model: string;
  // BYOK — единственный режим (ADR-HUB-0042); провайдер принадлежит агенту, а не каналу.
  providerIntegrationId: number | null;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
  persona: string;
  tone: string;
  instructions: string;
  knowledge: AgentKnowledgeRef[];
  portalArticles: AgentPortalArticleRef[];
};
