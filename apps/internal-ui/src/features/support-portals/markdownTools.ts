import type { MarkdownTool } from "../../shared/markdown/markdownTools";

// Панель Markdown редактора статьи (дизайн-базлайн v2, кадр PT7).
export const MARKDOWN_TOOLS: MarkdownTool[] = [
  { key: "h1", title: "Заголовок 1", text: "H1" },
  { key: "h2", title: "Заголовок 2", text: "H2" },
  { key: "divider-1", title: "", divider: true },
  { key: "bold", title: "Полужирный", icon: "bold" },
  { key: "italic", title: "Курсив", icon: "italic" },
  { key: "link", title: "Ссылка", icon: "link" },
  { key: "code", title: "Код", icon: "code" },
  { key: "divider-2", title: "", divider: true },
  { key: "list", title: "Список", icon: "list" },
  { key: "numlist", title: "Нумерованный список", icon: "numlist" },
  { key: "quote", title: "Цитата", icon: "quote" },
  { key: "table", title: "Таблица", icon: "table" },
  { key: "divider-3", title: "", divider: true },
  { key: "image", title: "Вставить изображение", icon: "image", accent: true },
  { key: "attach", title: "Прикрепить файл", icon: "attach" },
];
