import type { PortalThemeSchemeSetting } from "./themes/types";

export type HelpProduct = {
  code: string;
  name: string;
  siteUrl: string;
  supportAvailable: boolean;
  supportWidgetKey: string | null;
  supportChannelCode: string | null;
};

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

export type HelpArticle = {
  slug: string;
  locale: string;
  category: HelpCategory;
  revision: HelpRevision;
  updatedAt: string;
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
  products: HelpProduct[];
};

export type HelpManifest = {
  portal: HelpPortal;
  categories: HelpCategory[];
};
