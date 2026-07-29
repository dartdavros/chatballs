import { api } from "../../api/client";
import type { Channel } from "../channels/types";
import type {
  ArticleRevision,
  PortalArticle,
  PortalCategory,
  PortalInput,
  PortalStatus,
  SupportPortal,
  SupportPortalList,
} from "./model";

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
  input: Partial<PortalInput>,
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
): Promise<{ items: Channel[]; widgetItems: Channel[] }> {
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
