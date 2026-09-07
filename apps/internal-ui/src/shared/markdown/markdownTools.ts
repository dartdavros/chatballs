import type { Icon } from "../icons";

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

const TABLE_SNIPPET = "\n| Колонка | Колонка |\n| ------- | ------- |\n| Значение | Значение |\n";

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
    const label = selected || "текст ссылки";
    const snippet = `[${label}](https://)`;
    const next = `${value.slice(0, selectionStart)}${snippet}${value.slice(selectionEnd)}`;
    const linkStart = selectionStart + snippet.length - 9;
    return { value: next, selectionStart: linkStart, selectionEnd: linkStart + 8 };
  }

  if (key === "table") {
    const next = `${value.slice(0, selectionStart)}${TABLE_SNIPPET}${value.slice(selectionEnd)}`;
    const caret = selectionStart + TABLE_SNIPPET.length;
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
  const characters = value.length.toLocaleString("ru-RU");
  const paragraphs = value.split(/\n{2,}/).filter((block) => block.trim()).length;
  const forms = paragraphs % 10 === 1 && paragraphs % 100 !== 11 ? "абзац"
    : [2, 3, 4].includes(paragraphs % 10) && ![12, 13, 14].includes(paragraphs % 100) ? "абзаца"
      : "абзацев";
  return `${characters} знаков · ${paragraphs} ${forms}`;
}

/** «Строка 18, столбец 24» — позиция курсора в статусной строке. */
export function cursorPosition(value: string, caret: number): string {
  const before = value.slice(0, caret);
  const line = before.split("\n").length;
  const column = caret - (before.lastIndexOf("\n") + 1) + 1;
  return `Строка ${line}, столбец ${column}`;
}

/** «PNG · 240 КБ» — метаданные файла в рейке. */
export function fileMeta(name: string, size: number): string {
  const extension = (name.split(".").pop() ?? "").toLocaleUpperCase();
  const kilobytes = size / 1024;
  const readable = kilobytes >= 1024
    ? `${(kilobytes / 1024).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} МБ`
    : `${Math.max(1, Math.round(kilobytes)).toLocaleString("ru-RU")} КБ`;
  return extension ? `${extension} · ${readable}` : readable;
}
