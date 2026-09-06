import { ApiError } from "../../api/client";
import type { PortalThemeSchemeSetting } from "../help-center/themes/types";

export type PortalStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";
export type ArticleStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";
export type PortalWidgetOption = {
  id: number;
  code: string;
  publicKey: string;
  name: string;
  mode: "ANONYMOUS" | "AUTHENTICATED_PRODUCT";
  status: "DRAFT" | "PUBLISHED" | "DISABLED";
  channel: {
    id: number;
    code: string;
    name: string;
    productId: number | null;
  } | null;
};

export type PortalProductLink = {
  productId: number;
  code: string;
  name: string;
  supportChannelId: number | null;
  supportChannelCode: string | null;
  supportWidgetId: number | null;
  supportWidgetKey: string | null;
  sortOrder: number;
};

export type SupportPortal = {
  id: number;
  publicId: string;
  slug: string;
  hostedDomain: string;
  customDomain: string | null;
  customDomainAddress: {
    name: string;
    type: "A";
    value: string;
  } | null;
  customDomainVerifiedAt: string | null;
  customDomainVerification: {
    name: string;
    type: "TXT";
    value: string;
  } | null;
  publicUrl: string;
  name: string;
  defaultLocale: string;
  theme: string;
  themeScheme: PortalThemeSchemeSetting;
  themeSettings: Record<string, string>;
  status: PortalStatus;
  publishedAt: string | null;
  widgetId: number | null;
  widgetKey: string | null;
  widgetChannelId: number | null;
  widgetChannelCode: string | null;
  products: PortalProductLink[];
  createdAt: string;
  updatedAt: string;
};

export type PortalCategory = {
  id: number;
  slug: string;
  name: string;
  description: string;
  parentId: number | null;
  sortOrder: number;
  articleCount: number;
};

export type ArticleRevision = {
  id: number;
  revision: number;
  title: string;
  summary: string;
  content: string;
  createdAt: string;
  publishedAt: string | null;
};

export type PortalArticle = {
  id: number;
  slug: string;
  locale: string;
  status: ArticleStatus;
  category: PortalCategory;
  publishedRevision: ArticleRevision | null;
  latestRevision: Omit<ArticleRevision, "content"> | null;
  revisions?: ArticleRevision[];
  createdAt: string;
  updatedAt: string;
};

export type PortalInput = {
  slug: string;
  name: string;
  defaultLocale: string;
  widgetId?: number | null;
  theme?: string;
  themeScheme?: PortalThemeSchemeSetting;
  themeSettings?: Record<string, string>;
};

export type PortalAddressConfig = {
  scheme: string;
  baseDomain: string;
  port: string | null;
};

export type SupportPortalList = {
  items: SupportPortal[];
  address: PortalAddressConfig;
};

export {
  addArticleRevision,
  archivePortalArticle,
  changePortalStatus,
  createPortalArticle,
  createPortalCategory,
  createSupportPortal,
  deletePortalCategory,
  importPortalArticles,
  listPortalArticles,
  listPortalCategories,
  listPortalSupportChannels,
  listSupportPortals,
  loadPortalArticle,
  loadSupportPortal,
  publishArticleRevision,
  replacePortalProducts,
  setPortalCustomDomain,
  updatePortalArticle,
  updatePortalCategory,
  updateSupportPortal,
  verifyPortalCustomDomain,
} from "./api";

export const PORTAL_STATUS_LABEL: Record<PortalStatus, string> = {
  DRAFT: "Черновик",
  PUBLISHED: "Опубликован",
  ARCHIVED: "В архиве",
};

export const ARTICLE_STATUS_LABEL: Record<ArticleStatus, string> = {
  DRAFT: "Черновик",
  PUBLISHED: "Опубликована",
  ARCHIVED: "В архиве",
};

type ValidationPayload = {
  detail?: string;
  errors?: Record<string, string[]>;
};

export function portalErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  const payload = error.payload as ValidationPayload;
  const first = payload.errors
    ? Object.values(payload.errors).flat().find(Boolean)
    : undefined;
  if (first && /[А-Яа-яЁё]/.test(first)) return first;
  if (error.status === 403) return "Недостаточно прав для этого действия";
  if (error.status === 404) return "Запись не найдена";
  if (error.status === 409) return "Изменение конфликтует с текущими данными";
  if (error.status === 429) return "Слишком много запросов. Повторите позже";
  return fallback;
}

export function portalFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) return {};
  const payload = error.payload as ValidationPayload;
  return Object.fromEntries(
    Object.entries(payload.errors ?? {}).map(([field, messages]) => [
      field,
      messages.find((message) => /[А-Яа-яЁё]/.test(message)) ?? "Проверьте значение",
    ]),
  );
}
