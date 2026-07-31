import { load as parseYaml } from "js-yaml";

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
    throw new Error(error instanceof Error ? `Невалидный YAML: ${error.message}` : "Невалидный YAML");
  }
  if (!data || typeof data !== "object") {
    throw new Error("Ожидается объект верхнего уровня с ключом articles");
  }
  const root = data as { articles?: unknown };
  if (!Array.isArray(root.articles) || root.articles.length === 0) {
    throw new Error("articles должен быть непустым списком");
  }
  const articles: ArticleImportDocument[] = [];
  root.articles.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(`Статья #${index + 1}: должна быть объектом`);
    }
    const record = item as Record<string, unknown>;
    const slug = record.slug === undefined || record.slug === null ? "" : String(record.slug).trim().toLowerCase();
    if (!slug) {
      throw new Error(`Статья #${index + 1}: обязательное поле «slug» пустое`);
    }
    const title = record.title === undefined || record.title === null ? "" : String(record.title).trim();
    if (!title) {
      throw new Error(`Статья #${index + 1}: обязательное поле «title» пустое`);
    }
    const content = record.content === undefined || record.content === null ? "" : String(record.content);
    if (!content.trim()) {
      throw new Error(`Статья #${index + 1}: обязательное поле «content» пустое`);
    }
    if (!Array.isArray(record.categoryPath) || record.categoryPath.length === 0) {
      throw new Error(`Статья #${index + 1}: обязательное поле «categoryPath» — непустой список разделов`);
    }
    const categoryPath: string[] = [];
    record.categoryPath.forEach((segment, segmentIndex) => {
      if (segment === undefined || segment === null || !String(segment).trim()) {
        throw new Error(`Статья #${index + 1}: раздел #${segmentIndex + 1} пустой`);
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
