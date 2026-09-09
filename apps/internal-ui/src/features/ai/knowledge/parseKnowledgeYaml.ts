import { load as parseYaml } from "js-yaml";
import { t } from "../../../i18n";

export type ParsedKnowledgeYaml = {
  documents: Array<{ title: string; description?: string; content: string; categoryPath?: string[] }>;
};

// Парсит YAML импорта знаний (SPEC-CHATBALLS-0012, плоский формат ADR-CHATBALLS-0023):
// { documents: [{ title, description?, content, categoryPath? }] }. Бросает
// Error с человекочитаемым сообщением при невалидном YAML или структуре.
// Путь категории разбирается, но не проверяется: несуществующий путь — это
// замечание в предпросмотре импорта (кадр KB8), а не поломка файла.
export function parseKnowledgeYaml(text: string): ParsedKnowledgeYaml {
  let data: unknown;
  try {
    data = parseYaml(text);
  } catch (error) {
    throw new Error(error instanceof Error ? t("ai.invalid_yaml_reason", { reason: error.message }) : t("ai.invalid_yaml"));
  }
  if (!data || typeof data !== "object") {
    throw new Error(t("ai.top_level_object_with_documents"));
  }
  const root = data as { documents?: unknown };
  if (!Array.isArray(root.documents) || root.documents.length === 0) {
    throw new Error(t("ai.documents_must_non_empty_list"));
  }
  const documents: ParsedKnowledgeYaml["documents"] = [];
  root.documents.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(t("ai.document_must_be_object", { index: index + 1 }));
    }
    const record = item as Record<string, unknown>;
    const title = record.title === undefined || record.title === null ? "" : String(record.title).trim();
    if (!title) {
      throw new Error(t("ai.document_title_empty", { index: index + 1 }));
    }
    const content = record.content === undefined || record.content === null ? "" : String(record.content);
    if (!content.trim()) {
      throw new Error(t("ai.document_content_empty", { index: index + 1 }));
    }
    const doc: ParsedKnowledgeYaml["documents"][number] = { title, content };
    if (record.description !== undefined && record.description !== null && String(record.description).trim()) {
      doc.description = String(record.description).trim();
    }
    if (record.categoryPath !== undefined && record.categoryPath !== null) {
      if (!Array.isArray(record.categoryPath) || record.categoryPath.length === 0) {
        throw new Error(t("ai.document_category_path_list", { index: index + 1 }));
      }
      const path = record.categoryPath.map((name) => String(name).trim());
      if (path.some((name) => !name)) {
        throw new Error(t("ai.document_category_path_empty_level", { index: index + 1 }));
      }
      doc.categoryPath = path;
    }
    documents.push(doc);
  });
  return { documents };
}
