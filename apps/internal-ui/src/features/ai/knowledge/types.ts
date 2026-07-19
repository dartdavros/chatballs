export type KnowledgeVisibility = "ORGANIZATION" | "DEPARTMENTS";

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

export type KnowledgeDepartmentReference = {
  id: number;
  code: string;
  name: string;
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
  visibility: KnowledgeVisibility;
  departments: KnowledgeDepartmentReference[];
  isEnabled: boolean;
  attachments: KnowledgeAttachment[];
  agentsCount: number | null;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeListFilters = {
  category?: number;
  department?: number;
  visibility?: KnowledgeVisibility;
  isEnabled?: boolean;
  search?: string;
};

export type KnowledgeCreateRequest = {
  title: string;
  description?: string;
  content?: string;
  categoryId?: number;
  visibility?: KnowledgeVisibility;
  departmentIds?: number[];
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

export type KnowledgeBulkVisibilityRequest = {
  knowledgeIds: number[];
  visibility: KnowledgeVisibility;
  departmentIds: number[];
};

export type KnowledgeBulkResult = {
  updated: number;
  knowledgeIds: number[];
};

export type AgentCategoryKnowledgeSelectionResult = {
  agentId: number;
  categoryId: number;
  addedKnowledgeIds: number[];
  knowledgeIds: number[];
};

export type KnowledgeScopeConflict = {
  agent: { id: number; name: string };
  knowledge: { id: number; title: string };
};

export type KnowledgeScopeConflictResponse = {
  code: "agent_knowledge_scope_conflict";
  detail: string;
  conflicts: KnowledgeScopeConflict[];
};

export type KnowledgeImportDocument = {
  title: string;
  description?: string;
  content: string;
  categoryPath?: string[];
  visibility?: KnowledgeVisibility;
  departmentCodes?: string[];
};

export type KnowledgeImportReport = {
  created: number;
  updated: number;
  unchanged: number;
  failed: Array<{ title: string; detail: string }>;
};
