import type { PortalThemeSchemeSetting } from "./themes/types";

export type HelpCategory = {
  id: number;
  slug: string;
  name: string;
  description: string;
  parentId: number | null;
  sortOrder: number;
  articleCount: number;
};

export type HelpRevision = {
  id: number;
  revision: number;
  title: string;
  summary: string;
  content?: string;
  createdAt: string;
  publishedAt: string | null;
};

export type HelpAttachment = {
  name: string;
  path: string;
  size: number;
  contentType: string;
};

export type HelpArticle = {
  slug: string;
  locale: string;
  category: HelpCategory;
  revision: HelpRevision;
  updatedAt: string;
  // Файлы статьи: картинки вставлены в текст, остальное посетитель скачивает.
  attachments?: HelpAttachment[];
};

export type HelpPortal = {
  slug: string;
  name: string;
  defaultLocale: string;
  theme: string;
  themeScheme: PortalThemeSchemeSetting;
  themeSettings: Record<string, string>;
  webWidgetKey: string | null;
  webWidgetChannelCode: string | null;
};

export type HelpManifest = {
  portal: HelpPortal;
  categories: HelpCategory[];
};
