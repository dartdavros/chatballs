import { ApiError, api, apiUpload } from "../../../api/client";
import type {
  AgentCategoryKnowledgeSelectionResult,
  KnowledgeAttachment,
  KnowledgeBulkMoveRequest,
  KnowledgeBulkResult,
  KnowledgeBulkVisibilityRequest,
  KnowledgeCategory,
  KnowledgeCategoryCreateRequest,
  KnowledgeCategoryUpdateRequest,
  KnowledgeCreateRequest,
  KnowledgeImportDocument,
  KnowledgeImportReport,
  KnowledgeItem,
  KnowledgeListFilters,
  KnowledgeScopeConflictResponse,
  KnowledgeUpdateRequest,
} from "./types";

export function isKnowledgeScopeConflict(
  error: unknown,
): error is ApiError<KnowledgeScopeConflictResponse> {
  return error instanceof ApiError
    && error.status === 409
    && error.payload.code === "agent_knowledge_scope_conflict"
    && Array.isArray(error.payload.conflicts);
}

function knowledgeListPath(filters: KnowledgeListFilters): string {
  const query = new URLSearchParams();
  if (filters.category !== undefined) query.set("category", String(filters.category));
  if (filters.department !== undefined) query.set("department", String(filters.department));
  if (filters.visibility !== undefined) query.set("visibility", filters.visibility);
  if (filters.isEnabled !== undefined) query.set("isEnabled", String(filters.isEnabled));
  if (filters.search !== undefined && filters.search !== "") query.set("search", filters.search);
  const suffix = query.toString();
  return `/api/v1/ai/knowledge/${suffix ? `?${suffix}` : ""}`;
}

export function fetchKnowledgeList(filters: KnowledgeListFilters = {}) {
  return api<{ items: KnowledgeItem[] }>(knowledgeListPath(filters));
}

export function fetchKnowledgeItem(id: number) {
  return api<{ knowledge: KnowledgeItem }>(`/api/v1/ai/knowledge/${id}/`);
}

export function createKnowledgeItem(data: KnowledgeCreateRequest) {
  return api<{ knowledge: KnowledgeItem }>("/api/v1/ai/knowledge/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateKnowledgeItem(id: number, data: KnowledgeUpdateRequest) {
  return api<{ knowledge: KnowledgeItem }>(`/api/v1/ai/knowledge/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteKnowledgeItem(id: number) {
  return api<void>(`/api/v1/ai/knowledge/${id}/`, { method: "DELETE" });
}

export function fetchKnowledgeCategories() {
  return api<{ items: KnowledgeCategory[] }>("/api/v1/ai/knowledge/categories/");
}

export function createKnowledgeCategory(data: KnowledgeCategoryCreateRequest) {
  return api<{ category: KnowledgeCategory }>("/api/v1/ai/knowledge/categories/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateKnowledgeCategory(id: number, data: KnowledgeCategoryUpdateRequest) {
  return api<{ category: KnowledgeCategory }>(`/api/v1/ai/knowledge/categories/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteKnowledgeCategory(id: number) {
  return api<void>(`/api/v1/ai/knowledge/categories/${id}/`, { method: "DELETE" });
}

export function bulkMoveKnowledge(data: KnowledgeBulkMoveRequest) {
  return api<KnowledgeBulkResult>("/api/v1/ai/knowledge/bulk/move/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function bulkReplaceKnowledgeVisibility(data: KnowledgeBulkVisibilityRequest) {
  return api<KnowledgeBulkResult>("/api/v1/ai/knowledge/bulk/visibility/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function selectAgentCategoryKnowledge(agentId: number, categoryId: number) {
  return api<AgentCategoryKnowledgeSelectionResult>(
    `/api/v1/ai/agents/${agentId}/knowledge/select-category/`,
    { method: "POST", body: JSON.stringify({ categoryId }) },
  );
}

export function uploadAttachment(knowledgeId: number, file: File) {
  const form = new FormData();
  form.append("file", file, file.name);
  return apiUpload<{ attachment: KnowledgeAttachment }>(
    `/api/v1/ai/knowledge/${knowledgeId}/attachments/`,
    form,
  );
}

export function deleteAttachment(knowledgeId: number, attachmentId: number) {
  return api<void>(`/api/v1/ai/knowledge/${knowledgeId}/attachments/${attachmentId}/`, {
    method: "DELETE",
  });
}

export function importKnowledge(documents: KnowledgeImportDocument[]) {
  return api<KnowledgeImportReport>("/api/v1/ai/knowledge/import/", {
    method: "POST",
    body: JSON.stringify({ documents }),
  });
}
