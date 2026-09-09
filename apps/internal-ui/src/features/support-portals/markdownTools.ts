import type { MarkdownTool } from "../../shared/markdown/markdownTools";
import { t } from "../../i18n";

// Панель Markdown редактора статьи (дизайн-базлайн v2, кадр PT7).
export const MARKDOWN_TOOLS: MarkdownTool[] = [
  { key: "h1", title: t("ai.heading_1"), text: "H1" },
  { key: "h2", title: t("ai.heading_2"), text: "H2" },
  { key: "divider-1", title: "", divider: true },
  { key: "bold", title: t("ai.bold"), icon: "bold" },
  { key: "italic", title: t("ai.italic"), icon: "italic" },
  { key: "link", title: t("ai.link"), icon: "link" },
  { key: "code", title: t("ai.code"), icon: "code" },
  { key: "divider-2", title: "", divider: true },
  { key: "list", title: t("ai.list"), icon: "list" },
  { key: "numlist", title: t("ai.numbered_list"), icon: "numlist" },
  { key: "quote", title: t("ai.quote"), icon: "quote" },
  { key: "table", title: t("ai.table"), icon: "table" },
  { key: "divider-3", title: "", divider: true },
  { key: "image", title: t("portals.insert_image"), icon: "image", accent: true },
  { key: "attach", title: t("common.attach_file"), icon: "attach" },
];
