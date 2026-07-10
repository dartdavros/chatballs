import type { ChannelRef } from "../model";

export type AiAgentDetail = {
  id: number;
  channel: ChannelRef;
  name: string;
  isActive: boolean;
  model: string;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
};

export type DocVersion = {
  id: number;
  version: number;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  content: string;
  createdBy: number | null;
  createdAt: string;
};

export type KnowledgeDoc = {
  id: number;
  scope: "GLOBAL" | "PRODUCT";
  product: { code: string; name: string } | null;
  code: string;
  title: string;
  category: string;
  isEnabled: boolean;
  inclusionMode: "MANDATORY" | "RETRIEVAL";
  versions: DocVersion[];
  createdAt: string;
  updatedAt: string;
};

export type PromptDoc = {
  id: number;
  scope: "GLOBAL" | "PRODUCT";
  product: { code: string; name: string } | null;
  code: string;
  title: string;
  category: string;
  isEnabled: boolean;
  versions: DocVersion[];
  createdAt: string;
  updatedAt: string;
};

export type AiReleaseFull = {
  id: number;
  channel: ChannelRef;
  version: number;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  model: string;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
  notes: string;
  retrievalIndexVersion: string;
  knowledgeVersions: Array<{ document: string; version: number }>;
  promptVersions: Array<{ document: string; version: number }>;
  createdAt: string;
  publishedAt: string | null;
};

export type AgentTab = "overview" | "instructions" | "knowledge" | "releases" | "metrics";

export const agentTabs: Array<{ key: AgentTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "instructions", label: "Инструкции" },
  { key: "knowledge", label: "Знания" },
  { key: "releases", label: "История версий" },
  { key: "metrics", label: "Метрики" },
];

const RELEASE_TONE: Record<AiReleaseFull["status"], { bg: string; color: string; label: string }> = {
  PUBLISHED: { bg: "#f6ffed", color: "#389e0d", label: "Опубликована" },
  DRAFT: { bg: "#fff7e6", color: "#d48806", label: "Черновик версии" },
  ARCHIVED: { bg: "#f5f5f5", color: "#8c8c8c", label: "Архив" },
};

export function releaseTone(status: AiReleaseFull["status"]) {
  return RELEASE_TONE[status];
}

const KNOWLEDGE_CATEGORY: Record<string, string> = {
  OVERVIEW: "Обзор продукта",
  AUDIENCE: "Целевая аудитория",
  COMMERCIAL: "Коммерческая модель",
  TECHNICAL: "Техническая информация",
  FAQ: "FAQ",
  OBJECTIONS: "Возражения",
  LIMITATIONS: "Ограничения",
};

const PROMPT_CATEGORY: Record<string, string> = {
  SYSTEM: "Системный промпт",
  QUALIFICATION: "Квалификация",
  SALES_BEHAVIOR: "Поведение в продаже",
  OPERATOR_HANDOFF: "Передача оператору",
};

export function knowledgeCategoryLabel(category: string): string {
  return KNOWLEDGE_CATEGORY[category] ?? category;
}

export function promptCategoryLabel(category: string): string {
  return PROMPT_CATEGORY[category] ?? category;
}

export const knowledgeCategoryOptions = Object.entries(KNOWLEDGE_CATEGORY).map(([value, label]) => ({ value, label }));
export const promptCategoryOptions = Object.entries(PROMPT_CATEGORY).map(([value, label]) => ({ value, label }));

export function publishedVersion(versions: DocVersion[]): DocVersion | undefined {
  return versions.find((version) => version.status === "PUBLISHED") ?? versions[0];
}

export function publishedRelease(releases: AiReleaseFull[]): AiReleaseFull | undefined {
  return releases.find((release) => release.status === "PUBLISHED");
}

export function releaseDisplayName(release: AiReleaseFull): string {
  const letters = release.channel.name.match(/[A-ZА-ЯЁ]/g)?.join("");
  const prefix = letters && letters.length >= 2 ? letters.slice(0, 2) : release.channel.code.slice(0, 2);
  return `REL-${prefix.toUpperCase()}-v${release.version}`;
}

// agent.limits — единый поддерживаемый лимит: дневной бюджет в целых центах USD (dailyCostUsd).
export function dailyBudget(limits: Record<string, unknown>): string {
  const cents = limits?.dailyCostUsd;
  if (typeof cents !== "number" || cents <= 0) return "—";
  return `$${(cents / 100).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / день`;
}
