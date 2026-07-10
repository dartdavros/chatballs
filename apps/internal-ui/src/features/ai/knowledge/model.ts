import { api, apiUpload } from "../../../api/client";

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
  isEnabled: boolean;
  attachments: KnowledgeAttachment[];
  agentsCount: number | null;
  createdAt: string;
  updatedAt: string;
};

export type KnowledgeImportReport = {
  created: number;
  updated: number;
  unchanged: number;
  failed: Array<{ title: string; detail: string }>;
};

export function fetchKnowledgeList() {
  return api<{ items: KnowledgeItem[] }>("/api/v1/ai/knowledge/");
}

export function fetchKnowledgeItem(id: number) {
  return api<{ knowledge: KnowledgeItem }>(`/api/v1/ai/knowledge/${id}/`);
}

export function createKnowledgeItem(data: { title: string; description: string; content: string }) {
  return api<{ knowledge: KnowledgeItem }>("/api/v1/ai/knowledge/", { method: "POST", body: JSON.stringify(data) });
}

export function updateKnowledgeItem(id: number, data: Partial<{ title: string; description: string; content: string; isEnabled: boolean }>) {
  return api<{ knowledge: KnowledgeItem }>(`/api/v1/ai/knowledge/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteKnowledgeItem(id: number) {
  return api<void>(`/api/v1/ai/knowledge/${id}/`, { method: "DELETE" });
}

export function uploadAttachment(knowledgeId: number, file: File) {
  const form = new FormData();
  form.append("file", file, file.name);
  return apiUpload<{ attachment: KnowledgeAttachment }>(`/api/v1/ai/knowledge/${knowledgeId}/attachments/`, form);
}

export function deleteAttachment(knowledgeId: number, attachmentId: number) {
  return api<void>(`/api/v1/ai/knowledge/${knowledgeId}/attachments/${attachmentId}/`, { method: "DELETE" });
}

export function importKnowledge(documents: Array<{ title: string; description?: string; content: string }>) {
  return api<KnowledgeImportReport>("/api/v1/ai/knowledge/import/", { method: "POST", body: JSON.stringify({ documents }) });
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}
