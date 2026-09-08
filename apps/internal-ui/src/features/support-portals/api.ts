import { api, apiUpload } from "../../api/client";
import type { PagedPayload } from "../../shared/usePagedResource";
import type { ArticleImportDocument } from "./parseArticleYaml";
import type {
  ArticleRevision,
  PortalArticle,
  PortalArticleFile,
  PortalCategory,
  PortalInput,
  PortalStatus,
  PortalWidgetOption,
  SupportPortal,
  SupportPortalList,
} from "./model";

// Страница списка порталов (кадр PT1): статус, поиск и номер страницы —
// параметры запроса, фильтровать в браузере нечего.
export type PortalListQuery = { status: string[]; search: string };

export function listSupportPortals(
  { status, search }: PortalListQuery = { status: [], search: "" },
  page = 1,
): Promise<SupportPortalList> {
  const params = new URLSearchParams({ page: String(page) });
  for (const value of status) params.append("status", value);
  if (search.trim()) params.set("q", search.trim());
  return api(`/api/v1/support/portals/?${params.toString()}`);
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

export function listPortalWidgets(
  portalId: number,
): Promise<{ items: PortalWidgetOption[] }> {
  return api(`/api/v1/support/portals/${portalId}/widgets/`);
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

// Страница библиотеки статей (кадр PT3): категория, язык, статус и поиск —
// тоже параметры запроса.
export type ArticleListQuery = {
  category?: number;
  locale: string[];
  status: string[];
  search: string;
};

export function listPortalArticles(
  id: number,
  { category, locale, status, search }: ArticleListQuery = { locale: [], status: [], search: "" },
  page = 1,
): Promise<PagedPayload<PortalArticle>> {
  const params = new URLSearchParams({ page: String(page) });
  if (category !== undefined) params.set("category", String(category));
  for (const value of locale) params.append("locale", value);
  for (const value of status) params.append("status", value);
  if (search.trim()) params.set("q", search.trim());
  return api(`/api/v1/support/portals/${id}/articles/?${params.toString()}`);
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

export function listArticleFiles(
  portalId: number,
  articleId: number,
): Promise<{ items: PortalArticleFile[] }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/files/`);
}

/** Загрузка файла статьи с прогрессом: рейка редактора показывает проценты. */
export function uploadArticleFile(
  portalId: number,
  articleId: number,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<{ file: PortalArticleFile }> {
  const body = new FormData();
  body.append("file", file);
  return apiUpload(
    `/api/v1/support/portals/${portalId}/articles/${articleId}/files/`,
    body,
    onProgress,
  );
}

export function deleteArticleFile(
  portalId: number,
  articleId: number,
  fileId: number,
): Promise<void> {
  return api(
    `/api/v1/support/portals/${portalId}/articles/${articleId}/files/${fileId}/`,
    { method: "DELETE" },
  );
}

export function archivePortalArticle(
  portalId: number,
  articleId: number,
): Promise<{ article: PortalArticle }> {
  return api(`/api/v1/support/portals/${portalId}/articles/${articleId}/archive/`, {
    method: "POST",
  });
}

export type ArticleImportReport = {
  created: number;
  updated: number;
  unchanged: number;
  failed: Array<{ slug?: string; detail: string }>;
};

export function importPortalArticles(
  portalId: number,
  articles: ArticleImportDocument[],
): Promise<ArticleImportReport> {
  return api(`/api/v1/support/portals/${portalId}/articles/import/`, {
    method: "POST",
    body: JSON.stringify({ articles }),
  });
}
