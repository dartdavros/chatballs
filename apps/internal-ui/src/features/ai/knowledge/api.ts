import { api, apiUpload } from "../../../api/client";
import type { PagedPayload } from "../../../shared/usePagedResource";
import type {
  AgentCategoryKnowledgeSelectionResult,
  AgentLinkRequest,
  AgentLinkResponse,
  KnowledgeAttachment,
  KnowledgeBulkMoveRequest,
  KnowledgeBulkResult,
  KnowledgeCategory,
  KnowledgeCategoryCreateRequest,
  KnowledgeCategoryUpdateRequest,
  KnowledgeCreateRequest,
  KnowledgeImportDocument,
  KnowledgeImportReport,
  KnowledgeItem,
  KnowledgeListFilters,
  KnowledgeUpdateRequest,
} from "./types";

function knowledgeListPath(filters: KnowledgeListFilters, page?: number): string {
  const query = new URLSearchParams();
  if (filters.category !== undefined) query.set("category", String(filters.category));
  if (filters.isEnabled !== undefined) query.set("isEnabled", String(filters.isEnabled));
  if (filters.search !== undefined && filters.search !== "") query.set("search", filters.search);
  for (const agent of filters.agents ?? []) query.append("agent", String(agent));
  if (page !== undefined) query.set("page", String(page));
  const suffix = query.toString();
  return `/api/v1/ai/knowledge/${suffix ? `?${suffix}` : ""}`;
}

// Библиотека знаний приходит страницей: фильтры и ветка категорий отрабатывают
// на сервере (кадр KB1).
export function fetchKnowledgeList(filters: KnowledgeListFilters = {}, page = 1) {
  return api<PagedPayload<KnowledgeItem>>(knowledgeListPath(filters, page));
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

/** Пересобрать фрагменты знания вручную (кадры KB1/KB4). */
export function reindexKnowledge(id: number) {
  return api<{ knowledge: KnowledgeItem }>(`/api/v1/ai/knowledge/${id}/reindex/`, {
    method: "POST",
  });
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

export function linkKnowledgeToAgent(data: AgentLinkRequest & { knowledgeIds: number[] }) {
  return api<AgentLinkResponse>("/api/v1/ai/knowledge/bulk/agent/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function linkPortalArticlesToAgent(data: AgentLinkRequest & { articleIds: number[] }) {
  return api<AgentLinkResponse>("/api/v1/ai/portal-articles/bulk/agent/", {
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
