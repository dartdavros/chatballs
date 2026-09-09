import { load as parseYaml } from "js-yaml";
import { t } from "../../i18n";

export type ArticleImportDocument = {
  slug: string;
  categoryPath: string[];
  locale?: string;
  title: string;
  summary?: string;
  content: string;
};

export type ParsedArticleYaml = {
  articles: ArticleImportDocument[];
};

// Парсит YAML импорта статей портала:
// { articles: [{ slug, categoryPath: [..], locale?, title, summary?, content }] }.
// Ключ совпадания — (slug, locale). Бросает Error с человекочитаемым сообщением
// при невалидном YAML или структуре.
export function parseArticleYaml(text: string): ParsedArticleYaml {
  let data: unknown;
  try {
    data = parseYaml(text);
  } catch (error) {
    throw new Error(error instanceof Error ? t("ai.invalid_yaml_reason", { reason: error.message }) : t("portals.invalid_yaml"));
  }
  if (!data || typeof data !== "object") {
    throw new Error(t("portals.top_level_object_with_articles"));
  }
  const root = data as { articles?: unknown };
  if (!Array.isArray(root.articles) || root.articles.length === 0) {
    throw new Error(t("portals.articles_must_non_empty_list"));
  }
  const articles: ArticleImportDocument[] = [];
  root.articles.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(t("portals.article_must_be_object", { index: index + 1 }));
    }
    const record = item as Record<string, unknown>;
    const slug = record.slug === undefined || record.slug === null ? "" : String(record.slug).trim().toLowerCase();
    if (!slug) {
      throw new Error(t("portals.article_slug_empty", { index: index + 1 }));
    }
    const title = record.title === undefined || record.title === null ? "" : String(record.title).trim();
    if (!title) {
      throw new Error(t("portals.article_title_empty", { index: index + 1 }));
    }
    const content = record.content === undefined || record.content === null ? "" : String(record.content);
    if (!content.trim()) {
      throw new Error(t("portals.article_content_empty", { index: index + 1 }));
    }
    if (!Array.isArray(record.categoryPath) || record.categoryPath.length === 0) {
      throw new Error(t("portals.article_category_path_required", { index: index + 1 }));
    }
    const categoryPath: string[] = [];
    record.categoryPath.forEach((segment, segmentIndex) => {
      if (segment === undefined || segment === null || !String(segment).trim()) {
        throw new Error(t("portals.article_section_empty", { index: index + 1, segment: segmentIndex + 1 }));
      }
      categoryPath.push(String(segment).trim());
    });
    const doc: ArticleImportDocument = { slug, categoryPath, title, content };
    if (record.locale !== undefined && record.locale !== null && String(record.locale).trim()) {
      doc.locale = String(record.locale).trim().toLowerCase();
    }
    if (record.summary !== undefined && record.summary !== null && String(record.summary).trim()) {
      doc.summary = String(record.summary).trim();
    }
    articles.push(doc);
  });
  return { articles };
}
