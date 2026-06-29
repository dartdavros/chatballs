import { createElement, type ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import { type AiReleaseFull, type KnowledgeDoc, type PromptDoc } from "../detail/model";

export type ReleaseCheck = {
  detail?: string;
  icon: ReactNode;
  label: string;
  tone: "ok" | "warn" | "error";
};

export type ReleaseChange = {
  sign: "+" | "~" | "—";
  text: string;
  tone: "add" | "change" | "neutral";
};

export function releaseLabel(release: AiReleaseFull): string {
  return `REL-${releasePrefix(release.channel)}-v${release.version}`;
}

function releasePrefix(channel: AiReleaseFull["channel"]): string {
  const letters = channel.name.match(/[A-ZА-ЯЁ]/g)?.join("");
  if (letters && letters.length >= 2) return letters.slice(0, 2).toUpperCase();
  const code = channel.code.replace(/[^a-zA-Zа-яА-ЯёЁ0-9]/g, "");
  return (code.slice(0, 2) || "AI").toUpperCase();
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

export function formatShortDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  const today = new Date();
  if (date.getFullYear() === today.getFullYear() && date.getMonth() === today.getMonth() && date.getDate() === today.getDate()) return "сегодня";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long" }).format(date);
}

export function formatParam(value: unknown): string {
  if (value === undefined || value === null || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString("ru-RU");
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export function toolLabel(tool: unknown): string {
  if (typeof tool === "string") return tool;
  if (tool && typeof tool === "object" && "name" in tool) return String((tool as { name: unknown }).name);
  return "—";
}

function checkIcon(tone: ReleaseCheck["tone"]) {
  const name = tone === "ok" ? "check" : tone === "error" ? "xCircle" : "warning";
  return createElement(Icon, { name, size: 16 });
}

export function buildChecks(release: AiReleaseFull): ReleaseCheck[] {
  return [
    { label: "Системный prompt задан", tone: release.promptVersions.length > 0 ? "ok" : "warn", detail: release.promptVersions.length > 0 ? undefined : "нет версий prompt", icon: checkIcon(release.promptVersions.length > 0 ? "ok" : "warn") },
    { label: "Обязательные знания в индексе", tone: release.knowledgeVersions.length > 0 ? "ok" : "warn", detail: release.knowledgeVersions.length > 0 ? undefined : "нет версий знаний", icon: checkIcon(release.knowledgeVersions.length > 0 ? "ok" : "warn") },
    { label: "Retrieval index собран", tone: release.retrievalIndexVersion ? "ok" : "warn", detail: release.retrievalIndexVersion ? undefined : "индекс не указан", icon: checkIcon(release.retrievalIndexVersion ? "ok" : "warn") },
    { label: "Инструменты сконфигурированы", tone: release.allowedTools.length > 0 ? "ok" : "warn", detail: release.allowedTools.length > 0 ? undefined : "нет разрешённых инструментов", icon: checkIcon(release.allowedTools.length > 0 ? "ok" : "warn") },
    { label: "Лимиты в допустимых границах", tone: Object.keys(release.limits).length > 0 ? "ok" : "warn", detail: Object.keys(release.limits).length > 0 ? undefined : "лимиты не заданы", icon: checkIcon(Object.keys(release.limits).length > 0 ? "ok" : "warn") },
    { label: "Sales behavior заполнен", tone: release.promptVersions.some((item) => item.document.toLowerCase().includes("sales")) ? "ok" : "warn", detail: release.promptVersions.some((item) => item.document.toLowerCase().includes("sales")) ? undefined : "раздел пуст", icon: checkIcon(release.promptVersions.some((item) => item.document.toLowerCase().includes("sales")) ? "ok" : "warn") },
  ];
}

export function checksSummary(checks: ReleaseCheck[]): { label: string; tone: ReleaseCheck["tone"] } {
  const errors = checks.filter((check) => check.tone === "error").length;
  const warnings = checks.filter((check) => check.tone === "warn").length;
  if (errors > 0) return { label: `${errors} ошибка`, tone: "error" };
  if (warnings > 0) return { label: `${warnings} предупреждение`, tone: "warn" };
  return { label: "Все пройдены", tone: "ok" };
}

export function canPublishRelease(release: AiReleaseFull, checks: ReleaseCheck[]): boolean {
  return release.status === "DRAFT" && checks.every((check) => check.tone === "ok");
}

export function validationBanner(checks: ReleaseCheck[], tested = true) {
  const summary = checksSummary(checks);
  if (summary.tone === "error") return { title: "Найдены ошибки валидации", note: "Исправьте отмеченные пункты в составе версии, затем перезапустите проверку.", tone: "error" as const };
  if (summary.tone === "warn") return { title: "Черновик версии неполный", note: "Заполните обязательные разделы, чтобы перейти к проверке.", tone: "warn" as const };
  if (!tested) return { title: "Готово к тестированию", note: "Проверки пройдены. Запустите тест-чат перед публикацией.", tone: "ok" as const };
  return { title: "Готово к публикации", note: "Все проверки пройдены, протестировано в тест-чате. Можно публиковать.", tone: "ok" as const };
}

export function releaseState(checks: ReleaseCheck[], published: boolean, tested = true): { className: string; label: string } {
  const summary = checksSummary(checks);
  if (published) return { className: "published", label: "Опубликован" };
  if (summary.tone === "error") return { className: "errors", label: "Ошибки валидации" };
  if (summary.tone === "warn") return { className: "incomplete", label: "Неполный черновик" };
  if (!tested) return { className: "ready-test", label: "Готов к тестированию" };
  return { className: "ready-publish", label: "Готов к публикации" };
}

export function findPublishedPeer(release: AiReleaseFull, releases: AiReleaseFull[]): AiReleaseFull | undefined {
  return releases.find((item) => item.channel.code === release.channel.code && item.status === "PUBLISHED" && item.id !== release.id);
}

export function buildChanges(release: AiReleaseFull, published: AiReleaseFull | undefined): ReleaseChange[] {
  if (!published) return [{ sign: "+", tone: "add", text: "Опубликованная версия отсутствует: черновик станет первой опубликованной версией." }];
  const changes: ReleaseChange[] = [];
  if (release.model !== published.model) changes.push({ sign: "~", tone: "change", text: "Модель и параметры отличаются от опубликованной версии." });
  if (JSON.stringify(release.promptVersions) !== JSON.stringify(published.promptVersions)) changes.push({ sign: "~", tone: "change", text: "Версии инструкций отличаются от опубликованной версии." });
  if (JSON.stringify(release.knowledgeVersions) !== JSON.stringify(published.knowledgeVersions)) changes.push({ sign: "~", tone: "change", text: "Состав знаний отличается от опубликованной версии." });
  if (release.retrievalIndexVersion !== published.retrievalIndexVersion) changes.push({ sign: "~", tone: "change", text: "Индекс поиска знаний отличается от опубликованной версии." });
  if (JSON.stringify(release.allowedTools) !== JSON.stringify(published.allowedTools)) changes.push({ sign: "~", tone: "change", text: "Набор инструментов отличается от опубликованной версии." });
  if (JSON.stringify(release.limits) !== JSON.stringify(published.limits)) changes.push({ sign: "~", tone: "change", text: "Лимиты отличаются от опубликованной версии." });
  return changes.length > 0 ? changes : [{ sign: "—", tone: "neutral", text: "Отличий от опубликованной версии не найдено." }];
}

export function promptTitle(prompts: PromptDoc[], code: string): string {
  return prompts.find((prompt) => prompt.code === code)?.title ?? code;
}

export function knowledgeTitle(knowledge: KnowledgeDoc[], code: string): string {
  return knowledge.find((document) => document.code === code)?.title ?? code;
}

export function promptVersionDate(prompts: PromptDoc[], code: string, version: number): string {
  const prompt = prompts.find((item) => item.code === code);
  const docVersion = prompt?.versions.find((item) => item.version === version);
  return formatShortDate(docVersion?.createdAt ?? prompt?.updatedAt);
}

export function isPromptChanged(published: AiReleaseFull | undefined, code: string, version: number): boolean {
  return published ? !published.promptVersions.some((item) => item.document === code && item.version === version) : true;
}

export function isKnowledgeChanged(published: AiReleaseFull | undefined, code: string, version: number): boolean {
  return published ? !published.knowledgeVersions.some((item) => item.document === code && item.version === version) : true;
}

export function limitLabel(key: string): string {
  const labels: Record<string, string> = {
    dailyBudgetRub: "Бюджет в день",
    dailyCostMicros: "Бюджет в день",
    dailyDialogs: "Диалогов в день",
    maxMessagesPerDialog: "Макс. сообщений / диалог",
  };
  return labels[key] ?? key;
}
