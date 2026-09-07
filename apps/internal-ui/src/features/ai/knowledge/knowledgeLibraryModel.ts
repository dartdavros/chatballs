import type { AgentCard } from "../../agents/model";
import { pluralRu, shortDateTime } from "../../../shared/utils";
import type { KnowledgeAttachment, KnowledgeCategory, KnowledgeItem } from "./types";

// Экранная модель раздела «База знаний» (дизайн-базлайн v2, кадры KB1–KB9).
// Отделы упразднены ADR-HUB-0041, поэтому доступность знания — это флаг
// «участвует в ответах» плюс явный список прикреплённых агентов.

export type CategoryRow = {
  category: KnowledgeCategory;
  depth: number;
  count: number;
};

/** Категории в порядке дерева с глубиной вложенности (левая панель KB1). */
export function categoryRows(categories: KnowledgeCategory[]): CategoryRow[] {
  const byParent = new Map<number | null, KnowledgeCategory[]>();
  categories.forEach((category) => {
    const siblings = byParent.get(category.parentId) ?? [];
    siblings.push(category);
    byParent.set(category.parentId, siblings);
  });
  byParent.forEach((items) => items.sort((left, right) => (
    left.sortOrder - right.sortOrder || left.name.localeCompare(right.name, "ru")
  )));
  const rows: CategoryRow[] = [];
  const walk = (parentId: number | null, depth: number) => {
    (byParent.get(parentId) ?? []).forEach((category) => {
      rows.push({ category, depth, count: category.knowledgeCount ?? 0 });
      walk(category.id, depth + 1);
    });
  };
  walk(null, 0);
  return rows;
}

/** Все потомки категории вместе с ней — выбор в дереве включает вложенные. */
export function categoryBranch(categories: KnowledgeCategory[], categoryId: number): Set<number> {
  const branch = new Set<number>();
  const pending = [categoryId];
  while (pending.length) {
    const id = pending.pop()!;
    branch.add(id);
    categories.filter((item) => item.parentId === id).forEach((item) => pending.push(item.id));
  }
  return branch;
}

/** «9 категорий · 84 знания · 1 240 фрагментов» — подпись шапки (кадр KB1).
 *  Тысячи разделяются неразрывным пробелом, как в макете. */
export function libraryTotals(categories: KnowledgeCategory[], items: KnowledgeItem[]): string {
  const knowledge = categories
    .filter((category) => category.parentId === null)
    .reduce((total, category) => total + (category.knowledgeCount ?? 0), 0);
  const fragments = items.reduce((total, item) => total + (item.fragmentsCount ?? 0), 0);
  const fragmentsText = pluralRu(fragments, ["фрагмент", "фрагмента", "фрагментов"])
    .replace(String(fragments), fragments.toLocaleString("ru-RU"));
  return [
    pluralRu(categories.length, ["категория", "категории", "категорий"]),
    pluralRu(knowledge, ["знание", "знания", "знаний"]),
    fragmentsText,
  ].join(" · ");
}

/** Агенты, которым знание прикреплено явно (карточка и рейка редактора). */
export function agentsOfKnowledge(agents: AgentCard[], knowledgeId: number): AgentCard[] {
  return agents.filter((agent) => agent.knowledge.some((item) => item.id === knowledgeId));
}

export type AgentState = {
  agent: AgentCard;
  /** «AI отвечает» / «AI выключен у агента» — подпись строки агента. */
  meta: string;
  /** Участвует ли знание в ответах именно этого агента. */
  answering: boolean;
};

export function agentStates(agents: AgentCard[], knowledgeId: number): AgentState[] {
  return agentsOfKnowledge(agents, knowledgeId).map((agent) => ({
    agent,
    meta: agent.aiStatus === "ACTIVE" ? "AI отвечает" : "AI выключен у агента",
    answering: agent.aiStatus === "ACTIVE",
  }));
}

/** «5 сен, 11:20» — дата в колонке «Обновлено». */
export function knowledgeUpdatedAt(item: KnowledgeItem): string {
  return shortDateTime(item.updatedAt);
}

/** Подпись состояния знания в ответах агента (колонка «В ОТВЕТАХ»). */
export function answerStateLabel(item: KnowledgeItem): string {
  return item.isEnabled ? "Включено" : "Выключено";
}

/** «PDF · 1,1 МБ · ссылка в тексте» — подпись вложения (кадры KB4/KB5). */
export function attachmentMeta(attachment: KnowledgeAttachment, content = ""): string {
  const extension = (attachment.name.split(".").pop() ?? "").toLocaleUpperCase();
  const kilobytes = attachment.size / 1024;
  const size = kilobytes >= 1024
    ? `${(kilobytes / 1024).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} МБ`
    : `${Math.max(1, Math.round(kilobytes)).toLocaleString("ru-RU")} КБ`;
  const linked = content.includes(attachment.url) ? " · ссылка в тексте" : "";
  return `${extension ? `${extension} · ` : ""}${size}${linked}`;
}

export function isImageAttachment(attachment: KnowledgeAttachment): boolean {
  return attachment.contentType.startsWith("image/") || /\.(png|jpe?g|webp|gif|svg)$/i.test(attachment.name);
}

/** Ссылка на вложение в Markdown: картинка — изображением, файл — ссылкой. */
export function attachmentMarkdown(attachment: KnowledgeAttachment): string {
  return `${isImageAttachment(attachment) ? "!" : ""}[${attachment.name}](${attachment.url})`;
}

// Пустая строка — граница абзаца: тем же разделителем режет ai/chunking.py.
const BREAK = String.fromCharCode(10, 10);

/** Фрагменты знания по тому же правилу, что и индексатор (ai/chunking.py):
 *  абзацы упаковываются по 800 знаков. Нужен для строки «≈12 фрагментов»
 *  в статусе редактора до сохранения (кадр KB5). */
export function knowledgeChunks(content: string, maxChars = 800): string[] {
  const paragraphs = content.split(BREAK).map((block) => block.trim()).filter(Boolean);
  const chunks: string[] = [];
  let current = "";
  paragraphs.forEach((paragraph) => {
    if (current && current.length + paragraph.length + 2 > maxChars) {
      chunks.push(current);
      current = paragraph;
    } else {
      current = current ? current + BREAK + paragraph : paragraph;
    }
  });
  if (current) chunks.push(current);
  return chunks;
}

/** «4 280 знаков · ≈12 фрагментов» — статусная строка редактора (кадр KB5). */
export function knowledgeEditorStats(content: string): string {
  const characters = content.length.toLocaleString("ru-RU");
  return `${characters} знаков · ≈${pluralRu(knowledgeChunks(content).length, ["фрагмент", "фрагмента", "фрагментов"])}`;
}
