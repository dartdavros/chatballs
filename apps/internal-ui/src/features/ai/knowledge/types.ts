export type KnowledgeCategoryReference = {
  id: number;
  name: string;
  parentId: number | null;
};

export type KnowledgeCategory = KnowledgeCategoryReference & {
  sortOrder: number;
  isSystem: boolean;
  knowledgeCount: number | null;
};

export type KnowledgeAttachment = {
  id: number;
  name: string;
  contentType: string;
  size: number;
  hasText: boolean;
  url: string;
  createdAt: string;
};

export type KnowledgeItem = {
  id: number;
  title: string;
  description: string;
  content?: string;
  category: KnowledgeCategoryReference;
  isEnabled: boolean;
  attachments: KnowledgeAttachment[];
  agentsCount: number | null;
  createdBy?: string;
  // Кто последним правил знание — подпись под датой в колонке «Обновлено».
  updatedBy?: string;
  fragmentsCount: number | null;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeListFilters = {
  category?: number;
  isEnabled?: boolean;
  search?: string;
};

export type KnowledgeCreateRequest = {
  title: string;
  description?: string;
  content?: string;
  categoryId?: number;
  isEnabled?: boolean;
};

export type KnowledgeUpdateRequest = Partial<KnowledgeCreateRequest>;

export type KnowledgeCategoryCreateRequest = {
  name: string;
  parentId?: number | null;
  sortOrder?: number;
};

export type KnowledgeCategoryUpdateRequest = Partial<KnowledgeCategoryCreateRequest>;

export type KnowledgeBulkMoveRequest = {
  knowledgeIds: number[];
  categoryId: number;
};

export type KnowledgeBulkResult = {
  updated: number;
  knowledgeIds: number[];
};

export type AgentLinkRequest = {
  agentId: number;
  action: "attach" | "detach";
};

export type AgentLinkResponse = {
  agentId: number;
  action: "attach" | "detach";
  changed: number;
  changedIds: number[];
  skippedIds: number[];
};

export type AgentCategoryKnowledgeSelectionResult = {
  agentId: number;
  categoryId: number;
  addedKnowledgeIds: number[];
  knowledgeIds: number[];
};

export type KnowledgeImportDocument = {
  title: string;
  description?: string;
  content: string;
  categoryPath?: string[];
};

export type KnowledgeImportReport = {
  created: number;
  updated: number;
  unchanged: number;
  failed: Array<{ title: string; detail: string }>;
};
