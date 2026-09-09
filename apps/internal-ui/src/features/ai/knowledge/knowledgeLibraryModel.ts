import { readableSize, shortDateTime } from "../../../shared/utils";
import type { KnowledgeAgentRef, KnowledgeAttachment, KnowledgeCategory, KnowledgeItem } from "./types";
import { t, tn } from "../../../i18n";

// Экранная модель раздела «База знаний» (дизайн-базлайн v2, кадры KB1–KB9).
// Отделы упразднены ADR-CHATBALLS-0041, поэтому доступность знания — это флаг
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
  const fragmentsText = tn("plural.chunks", fragments)
    .replace(String(fragments), fragments.toLocaleString("ru-RU"));
  return [
    tn("plural.categories", categories.length),
    tn("plural.knowledge", knowledge),
    fragmentsText,
  ].join(" · ");
}

/** Агенты, которым знание прикреплено явно (карточка и рейка редактора). */
export type AgentState = {
  agent: KnowledgeAgentRef;
  /** «AI отвечает» / «AI выключен у агента» — подпись строки агента. */
  meta: string;
  /** Участвует ли знание в ответах именно этого агента. */
  answering: boolean;
};

/** Агенты материала приходят из его карточки: считать их по всем карточкам
 *  агентов организации больше не нужно. */
export function agentStates(agents: KnowledgeAgentRef[]): AgentState[] {
  return agents.map((agent) => ({
    agent,
    meta: agent.aiStatus === "ACTIVE" ? t("conversations.ai_replying") : t("ai.ai_off_agent"),
    answering: agent.aiStatus === "ACTIVE",
  }));
}

/** «5 сен, 11:20» — дата в колонке «Обновлено». */
export function knowledgeUpdatedAt(item: KnowledgeItem): string {
  return shortDateTime(item.updatedAt);
}

/** Подпись состояния знания в ответах агента (колонка «В ОТВЕТАХ»). */
export function answerStateLabel(item: KnowledgeItem): string {
  return item.isEnabled ? t("common.on") : t("common.off");
}

/** «PDF · 1,1 МБ · ссылка в тексте» — подпись вложения (кадры KB4/KB5). */
export function attachmentMeta(attachment: KnowledgeAttachment, content = ""): string {
  const extension = (attachment.name.split(".").pop() ?? "").toLocaleUpperCase();
  const size = readableSize(attachment.size);
  const linked = content.includes(attachment.url) ? t("ai.link_text") : "";
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
  return t("ai.characters_and_chunks", { characters, chunks: tn("plural.chunks", knowledgeChunks(content).length) });
}
