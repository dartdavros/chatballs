import { api } from "../../../api/client";
import type { DocVersion, KnowledgeDoc, PromptDoc } from "./model";

// Жизненный цикл документов знаний/промптов (бэкенд: hub_platform/ai/doc_views.py).
// kind совпадает с REST-префиксом: knowledge | prompts.
export type DocKind = "knowledge" | "prompts";

type DocPayload<K extends DocKind> = K extends "knowledge" ? KnowledgeDoc : PromptDoc;

function base(kind: DocKind): string {
  return `/api/v1/ai/${kind}`;
}

export function latestVersion(versions: DocVersion[]): DocVersion | undefined {
  return [...versions].sort((a, b) => b.version - a.version)[0];
}

export function hasUnpublishedDraft(versions: DocVersion[]): boolean {
  const latest = latestVersion(versions);
  return latest !== undefined && latest.status === "DRAFT";
}

async function addVersion<K extends DocKind>(kind: K, id: number, content: string): Promise<DocPayload<K>> {
  const { document } = await api<{ document: DocPayload<K> }>(`${base(kind)}/${id}/versions/`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  return document;
}

export async function publishVersion(kind: DocKind, id: number, version: number): Promise<void> {
  await api(`${base(kind)}/${id}/versions/${version}/publish/`, { method: "POST" });
}

// Сохранить новый черновик; при publish — сразу опубликовать только что созданную версию.
export async function saveDocVersion<K extends DocKind>(
  kind: K,
  id: number,
  content: string,
  publish: boolean,
): Promise<void> {
  const document = await addVersion(kind, id, content);
  if (publish) {
    const created = latestVersion(document.versions);
    if (created) await publishVersion(kind, id, created.version);
  }
}

export async function setDocEnabled(kind: DocKind, id: number, enabled: boolean): Promise<void> {
  await api(`${base(kind)}/${id}/${enabled ? "enable" : "disable"}/`, { method: "POST" });
}

export type CreateDocInput = {
  title: string;
  category: string;
  content: string;
  scope: "GLOBAL" | "PRODUCT";
  product?: string;
  inclusionMode?: "MANDATORY" | "RETRIEVAL";
};

function slugCode(title: string): string {
  // SlugField хранит ASCII; кириллица отбрасывается → fallback на "doc".
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 40);
  return `${slug || "doc"}-${Math.random().toString(36).slice(2, 6)}`;
}

export async function createDoc(kind: DocKind, input: CreateDocInput): Promise<void> {
  await api(`${base(kind)}/`, {
    method: "POST",
    body: JSON.stringify({ ...input, code: slugCode(input.title) }),
  });
}
