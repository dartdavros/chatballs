export type AgentKnowledgeRef = { id: number; title: string; isEnabled: boolean; updatedAt: string };

export type AgentPortalArticleRef = {
  id: number;
  title: string;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  portal: { id: number; name: string };
  publicUrl: string;
};
