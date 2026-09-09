import type { Icon } from "../icons";
import { fmt, t, tn } from "../../i18n";
import { readableSize } from "../utils";

type IconName = Parameters<typeof Icon>[0]["name"];

export type MarkdownTool = {
  key: string;
  title: string;
  text?: string;
  icon?: IconName;
  divider?: boolean;
  accent?: boolean;
};

// Общая механика Markdown-редактора: панель применяется к выделению, статусная
// строка считает знаки и позицию курсора. Используют статьи портала (кадр PT7)
// и знания (кадр KB5) — набор кнопок у них свой, поведение одно.

export type MarkdownEdit = { value: string; selectionStart: number; selectionEnd: number };

const WRAPS: Record<string, [string, string]> = {
  bold: ["**", "**"],
  italic: ["*", "*"],
  code: ["`", "`"],
};

const LINE_PREFIXES: Record<string, string> = {
  h1: "# ",
  h2: "## ",
  list: "- ",
  numlist: "1. ",
  quote: "> ",
};

// Заголовки в шаблоне таблицы переводятся, поэтому это функция, а не
// константа: константу посчитали бы один раз, ещё до выбора языка.
const tableSnippet = () => t("shared.table_template");

/** Применение кнопки панели к тексту с учётом выделения (кадр PT7). */
export function applyMarkdownTool(
  key: string,
  value: string,
  selectionStart: number,
  selectionEnd: number,
): MarkdownEdit {
  const selected = value.slice(selectionStart, selectionEnd);

  const wrap = WRAPS[key];
  if (wrap) {
    const [open, close] = wrap;
    const next = `${value.slice(0, selectionStart)}${open}${selected}${close}${value.slice(selectionEnd)}`;
    return {
      value: next,
      selectionStart: selectionStart + open.length,
      selectionEnd: selectionStart + open.length + selected.length,
    };
  }

  const prefix = LINE_PREFIXES[key];
  if (prefix) {
    const lineStart = value.lastIndexOf("\n", selectionStart - 1) + 1;
    const next = `${value.slice(0, lineStart)}${prefix}${value.slice(lineStart)}`;
    return {
      value: next,
      selectionStart: selectionStart + prefix.length,
      selectionEnd: selectionEnd + prefix.length,
    };
  }

  if (key === "link") {
    const label = selected || t("shared.link_text");
    const snippet = `[${label}](https://)`;
    const next = `${value.slice(0, selectionStart)}${snippet}${value.slice(selectionEnd)}`;
    const linkStart = selectionStart + snippet.length - 9;
    return { value: next, selectionStart: linkStart, selectionEnd: linkStart + 8 };
  }

  if (key === "table") {
    const next = `${value.slice(0, selectionStart)}${tableSnippet()}${value.slice(selectionEnd)}`;
    const caret = selectionStart + tableSnippet().length;
    return { value: next, selectionStart: caret, selectionEnd: caret };
  }

  return { value, selectionStart, selectionEnd };
}

/** Вставка файла: изображение — картинкой, документ — ссылкой (кадр PT8). */
export function fileMarkdown(name: string, url: string, isImage: boolean): string {
  return isImage ? `![${name}](${url})` : `[${name}](${url})`;
}

export function isImageFile(contentType: string, name: string): boolean {
  return contentType.startsWith("image/") || /\.(png|jpe?g|webp|gif|svg)$/i.test(name);
}

/** «4 280 знаков · 12 абзацев» — статусная строка редактора. */
export function editorStats(value: string): string {
  const paragraphs = value.split(/\n{2,}/).filter((block) => block.trim()).length;
  return t("shared.characters_and_paragraphs", {
    characters: fmt.number(value.length),
    paragraphs: tn("plural.paragraphs", paragraphs),
  });
}

/** «Строка 18, столбец 24» — позиция курсора в статусной строке. */
export function cursorPosition(value: string, caret: number): string {
  const before = value.slice(0, caret);
  const line = before.split("\n").length;
  const column = caret - (before.lastIndexOf("\n") + 1) + 1;
  return t("shared.line_column", { line, column });
}

/** «PNG · 240 КБ» — метаданные файла в рейке. */
export function fileMeta(name: string, size: number): string {
  const extension = (name.split(".").pop() ?? "").toLocaleUpperCase();
  const readable = readableSize(size);
  return extension ? `${extension} · ${readable}` : readable;
}
