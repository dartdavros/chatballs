import { api, ApiError } from "../../api/client";
import type { Channel } from "../channels/types";

export type PortalStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";
export type ArticleStatus = "DRAFT" | "PUBLISHED" | "ARCHIVED";

export type PortalProductLink = {
  productId: number;
  code: string;
  name: string;
  supportChannelId: number | null;
  supportChannelCode: string | null;
  sortOrder: number;
};

export type SupportPortal = {
  id: number;
  publicId: string;
  departmentCode: "support";
  slug: string;
  hostedDomain: string;
  customDomain: string | null;
  customDomainVerifiedAt: string | null;
  customDomainVerification: {
    name: string;
    type: "TXT";
    value: string;
  } | null;
  publicUrl: string;
  name: string;
  defaultLocale: string;
  status: PortalStatus;
  publishedAt: string | null;
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
};

export type PortalCreationPolicy = {
  available: boolean;
  canCreate: boolean;
  limit: number | null;
  used: number;
};

export type PortalAddressConfig = {
  scheme: string;
  baseDomain: string;
  port: string | null;
};

export type SupportPortalList = {
  items: SupportPortal[];
  creation: PortalCreationPolicy;
  address: PortalAddressConfig;
};

export function listSupportPortals(): Promise<SupportPortalList> {
  return api("/api/v1/support/portals/");
}

export function createSupportPortal(input: PortalInput): Promise<{ portal: SupportPortal }> {
  return api("/api/v1/support/portals/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function loadSupportPortal(id: number): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${id}/`);
}

export function updateSupportPortal(
  id: number,
  input: PortalInput,
): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function changePortalStatus(
  id: number,
  status: PortalStatus,
): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${id}/status/`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function replacePortalProducts(
  id: number,
  items: Array<{ productId: number; supportChannelId: number | null; sortOrder: number }>,
): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${id}/products/`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  });
}

export function listPortalCategories(id: number): Promise<{ items: PortalCategory[] }> {
  return api(`/api/v1/support/portals/${id}/categories/`);
}

export function createPortalCategory(
  id: number,
  input: Pick<PortalCategory, "name"> & Partial<Omit<PortalCategory, "id" | "articleCount" | "name">>,
): Promise<{ category: PortalCategory }> {
  return api(`/api/v1/support/portals/${id}/categories/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updatePortalCategory(
  portalId: number,
  categoryId: number,
  input: Partial<Omit<PortalCategory, "id" | "articleCount">>,
): Promise<{ category: PortalCategory }> {
  return api(`/api/v1/support/portals/${portalId}/categories/${categoryId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deletePortalCategory(
  portalId: number,
  categoryId: number,
): Promise<void> {
  return api(`/api/v1/support/portals/${portalId}/categories/${categoryId}/`, {
    method: "DELETE",
  });
}

export function listPortalSupportChannels(
  portalId: number,
): Promise<{ items: Channel[] }> {
  return api(`/api/v1/support/portals/${portalId}/support-channels/`);
}

export function setPortalCustomDomain(
  portalId: number,
  customDomain: string,
): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${portalId}/domain/`, {
    method: "PUT",
    body: JSON.stringify({ customDomain }),
  });
}

export function verifyPortalCustomDomain(
  portalId: number,
): Promise<{ portal: SupportPortal }> {
  return api(`/api/v1/support/portals/${portalId}/domain/verify/`, {
    method: "POST",
  });
}

export function listPortalArticles(id: number): Promise<{ items: PortalArticle[] }> {
  return api(`/api/v1/support/portals/${id}/articles/`);
}

export function createPortalArticle(
  portalId: number,
  input: {
    categoryId: number;
    slug: string;
    locale: string;
    title: string;
    summary: string;
    content: string;
  },
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function loadPortalArticle(
  portalId: number,
  articleId: number,
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/`);
}

export function updatePortalArticle(
  portalId: number,
  articleId: number,
  input: { categoryId: number; locale: string; slug: string },
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function addArticleRevision(
  portalId: number,
  articleId: number,
  input: Pick<ArticleRevision, "title" | "summary" | "content">,
): Promise<{ revision: ArticleRevision }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/revisions/`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function publishArticleRevision(
  portalId: number,
  articleId: number,
  revisionId: number,
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/publish/`, {
    method: "POST",
    body: JSON.stringify({ revisionId }),
  });
}

export function archivePortalArticle(
  portalId: number,
  articleId: number,
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/archive/`, {
    method: "POST",
  });
}

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
