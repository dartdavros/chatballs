import { api } from "../../api/client";
import type { HelpArticle, HelpManifest } from "./types";

export function fetchHelpManifest(): Promise<HelpManifest> {
  return api<HelpManifest>("/api/v1/help/");
}

export function fetchHelpArticles(
  options: { locale?: string; category?: string; query?: string; offset?: number } = {},
): Promise<{ items: HelpArticle[]; pagination: { hasMore: boolean; limit: number; offset: number; total: number } }> {
  const search = new URLSearchParams();
  if (options.locale) search.set("locale", options.locale);
  if (options.category) search.set("category", options.category);
  if (options.query) search.set("q", options.query);
  if (options.offset) search.set("offset", String(options.offset));
  const suffix = search.size ? `?${search.toString()}` : "";
  return api(`/api/v1/help/articles/${suffix}`);
}

export function fetchHelpArticle(
  articleSlug: string,
  locale?: string,
): Promise<{ article: HelpArticle }> {
  const suffix = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return api<{ article: HelpArticle }>(
    `/api/v1/help/articles/${encodeURIComponent(articleSlug)}/${suffix}`,
  );
}

export function sendArticleFeedback(
  articleSlug: string,
  helpful: boolean,
  locale?: string,
): Promise<{ ok: boolean }> {
  const suffix = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return api<{ ok: boolean }>(
    `/api/v1/help/articles/${encodeURIComponent(articleSlug)}/feedback/${suffix}`,
    { method: "POST", body: JSON.stringify({ helpful }) },
  );
}
