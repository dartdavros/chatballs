// Единая сущность «Агент» = канал + AI-конфигурация (ADR-CHATBALLS-0041 §4).
// Источник данных — агрегированный API /api/v1/agents/.
// Экранная модель — дизайн-базлайн v2, «Агенты Baseline», кадры G1–G5, S1.
import { api } from "../../api/client";
import { agentColorOf } from "../conversations/model";
import { channelMap, providerKey } from "../../shared/providers";
import { pluralRu, shortDate } from "../../shared/utils";
import type { AgentKnowledgeRef, AgentPortalArticleRef } from "../ai/model";

export type AgentConnection = {
  id: number;
  provider: string;
  name: string;
  status: string;
  // Чем подписана строка подключения: бот, ящик, домен сайта (кадры G3/G4).
  botUsername: string;
  email: string;
  allowedOrigins: string[];
  // Публичный ключ веб-виджета — из него собирается код вставки (кадр G4).
  widgetPublicKey: string;
};

export type AgentAiStatus = "DRAFT" | "ACTIVE" | "DISABLED";

export type AgentCard = {
  id: number;
  aiAgentId: number;
  code: string;
  name: string;
  isActive: boolean;
  groupId: number | null;
  groupName: string | null;
  groupColor: string;
  aiStatus: AgentAiStatus;
  model: string;
  providerIntegrationId: number | null;
  modelParams: Record<string, unknown>;
  limits: Record<string, unknown>;
  persona: string;
  tone: string;
  instructions: string;
  knowledge: AgentKnowledgeRef[];
  portalArticles: AgentPortalArticleRef[];
  // Сколько всего материалов можно выбрать: «4 из 18» в шапке блока «Знания».
  knowledgeTotal: number;
  connections: AgentConnection[];
  counters: { openConversations: number; connections: number };
  createdAt: string;
  updatedAt: string;
};

export type AgentPatch = Partial<{
  name: string;
  groupId: number | null;
  isActive: boolean;
  providerIntegrationId: number | null;
  persona: string;
  tone: string;
  instructions: string;
  knowledgeIds: number[];
  limits: Record<string, unknown>;
}>;

export function fetchAgents(): Promise<{ items: AgentCard[] }> {
  return api<{ items: AgentCard[] }>("/api/v1/agents/");
}

export function fetchAgent(agentId: number): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/`);
}

export function createAgent(input: { name: string; groupId: number | null }): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>("/api/v1/agents/", { method: "POST", body: JSON.stringify(input) });
}

export function patchAgent(agentId: number, patch: AgentPatch): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/`, { method: "PATCH", body: JSON.stringify(patch) });
}

export function deleteAgent(agentId: number): Promise<void> {
  return api<void>(`/api/v1/agents/${agentId}/`, { method: "DELETE" });
}

export function setAgentAiActive(agentId: number, active: boolean): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/${active ? "activate" : "deactivate"}/`, { method: "POST" });
}

export function bindAgentConnection(agentId: number, integrationId: number, force = false): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/connections/`, {
    method: "POST",
    body: JSON.stringify({ integrationId, force }),
  });
}

export function unbindAgentConnection(agentId: number, integrationId: number): Promise<{ agent: AgentCard }> {
  return api<{ agent: AgentCard }>(`/api/v1/agents/${agentId}/connections/${integrationId}/`, { method: "DELETE" });
}

export type AgentStatusTone = "active" | "paused" | "disabled";

// Статус карточки: канал выключен > AI активен > черновик. Подписи и цвета —
// таблица ST макета: «AI отвечает» на --ai, «Без AI» на предупреждении,
// «Выключен» серым.
const STATUS_META: Record<AgentStatusTone, { text: string; bg: string; color: string }> = {
  active: { text: "AI отвечает", bg: "color-mix(in srgb, var(--ai) 14%, var(--surface-card))", color: "var(--ai)" },
  paused: { text: "Без AI", bg: "var(--warning-bg)", color: "var(--warning-text)" },
  disabled: { text: "Выключен", bg: "var(--n-9)", color: "var(--n-4)" },
};

export function agentStatusTone(card: AgentCard): AgentStatusTone {
  if (!card.isActive) return "disabled";
  if (card.aiStatus === "ACTIVE") return "active";
  return "paused";
}

export function agentStatusMeta(card: AgentCard): { text: string; bg: string; color: string } {
  return STATUS_META[agentStatusTone(card)];
}

/** Плитка агента (кадры G1/G3): цвет из палитры по агенту, подложка — 12% от
 *  него; у выключенного агента плитка серая, как «Архив · Летняя акция». */
export function agentTile(card: Pick<AgentCard, "id" | "isActive">): { color: string; background: string } {
  const color = card.isActive ? agentColorOf(card.id) : "#8c8c8c";
  return { color, background: `color-mix(in srgb, ${color} 12%, var(--surface-card))` };
}

/** Модель в списке: пока провайдер не выбран, показывать нечего (кадр G1). */
export function agentModelLabel(card: AgentCard): string {
  return card.providerIntegrationId ? card.model : "—";
}

export function agentTint(provider: string): { color: string; bg: string; full: string } {
  const key = providerKey(provider);
  return key ? channelMap[key] : { color: "var(--n-4)", bg: "var(--n-9)", full: provider };
}

// Подпись строки подключения (кадры G3/G4): у Telegram — «Telegram · @bot»,
// у MAX — марка, у веб-виджета — домен сайта, у почты — адрес ящика.
export function connectionSubtitle(connection: AgentConnection): string {
  const key = providerKey(connection.provider);
  if (key === "TG") return connection.botUsername ? `Telegram · @${connection.botUsername}` : "Telegram";
  if (key === "WEB") return connection.allowedOrigins[0] ?? "Web-виджет";
  if (key === "EMAIL") return connection.email || "Email";
  return key ? channelMap[key].full : connection.provider;
}

// Таблица CS макета: подключено · ошибка · не проверено.
const CONNECTION_STATUS_META: Record<string, { text: string; bg: string; color: string }> = {
  OK: { text: "Подключено", bg: "var(--success-bg)", color: "var(--success-text)" },
  ERROR: { text: "Ошибка", bg: "var(--error-bg)", color: "var(--error-text)" },
};

export function connectionStatusMeta(status: string): { text: string; bg: string; color: string } {
  return CONNECTION_STATUS_META[status] ?? { text: "Не проверено", bg: "var(--n-9)", color: "var(--n-4)" };
}

/** «5 открытых диалогов» / «нет диалогов» — подзаголовок шапки карточки. */
export function openDialogsLine(count: number): string {
  return count === 0 ? "нет диалогов" : pluralRu(count, ["открытый диалог", "открытых диалога", "открытых диалогов"]);
}

/** «создан 12 мар 2026»; созданный сегодня — «сегодня» (кадр G5). */
export function createdLabel(value: string, now = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  if (date.toDateString() === now.toDateString()) return "сегодня";
  return `${shortDate(date)} ${date.getFullYear()}`;
}

export type AgentKnowledgeRow = {
  key: string;
  kind: "knowledge" | "article";
  id: number;
  title: string;
  icon: "doc" | "globe";
  chip: string;
  chipTone: "muted" | "accent";
  meta: string;
  href: string;
};

/** Строки блока «Знания»: сначала знания библиотеки, затем статьи порталов. */
export function knowledgeRows(card: AgentCard): AgentKnowledgeRow[] {
  return [
    ...card.knowledge.map((item): AgentKnowledgeRow => ({
      key: `k${item.id}`,
      kind: "knowledge",
      id: item.id,
      title: item.title,
      icon: "doc",
      chip: item.isEnabled ? "" : "Выключено",
      chipTone: "muted",
      meta: item.updatedAt ? `обновлено ${shortDate(item.updatedAt)}` : "",
      href: "",
    })),
    ...card.portalArticles.map((article): AgentKnowledgeRow => ({
      key: `a${article.id}`,
      kind: "article",
      id: article.id,
      title: article.title,
      icon: "globe",
      chip: `Портал · ${article.portal.name}`,
      chipTone: "accent",
      meta: "статья",
      href: article.publicUrl,
    })),
  ];
}

/** «4 из 18 · 3 знания + 1 статья» в шапке блока «Знания» (кадры G3/G4/G5). */
export function knowledgeLine(card: AgentCard): string {
  const knowledge = card.knowledge.length;
  const articles = card.portalArticles.length;
  const selected = knowledge + articles;
  if (selected === 0) return "ничего не выбрано";
  const head = `${selected} из ${card.knowledgeTotal}`;
  if (knowledge === 0 || articles === 0) return head;
  const parts = [
    pluralRu(knowledge, ["знание", "знания", "знаний"]),
    pluralRu(articles, ["статья", "статьи", "статей"]),
  ];
  return `${head} · ${parts.join(" + ")}`;
}

// Дневной бюджет агента хранится в целых центах USD (limits.dailyCostUsd,
// ADR-CHATBALLS-0023); на экране — доллары с двумя знаками.
export function dailyCostInput(limits: Record<string, unknown>): string {
  const cents = Number(limits.dailyCostUsd ?? 0);
  return Number.isFinite(cents) && cents > 0 ? (cents / 100).toFixed(2) : "";
}

export function dailyCostCents(value: string): number {
  const amount = Number(value.replace(",", ".").trim());
  if (!Number.isFinite(amount) || amount <= 0) return 0;
  return Math.round(amount * 100);
}
