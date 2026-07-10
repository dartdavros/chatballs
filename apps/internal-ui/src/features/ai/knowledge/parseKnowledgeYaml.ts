import { load as parseYaml } from "js-yaml";

export type ParsedKnowledgeYaml = {
  documents: Array<{ title: string; description?: string; content: string }>;
};

// Парсит YAML импорта знаний (SPEC-HUB-0012, плоский формат ADR-HUB-0023):
// { documents: [{ title, description?, content }] }. Бросает Error с
// человекочитаемым сообщением при невалидном YAML или структуре.
export function parseKnowledgeYaml(text: string): ParsedKnowledgeYaml {
  let data: unknown;
  try {
    data = parseYaml(text);
  } catch (error) {
    throw new Error(error instanceof Error ? `Невалидный YAML: ${error.message}` : "Невалидный YAML");
  }
  if (!data || typeof data !== "object") {
    throw new Error("Ожидается объект верхнего уровня с ключом documents");
  }
  const root = data as { documents?: unknown };
  if (!Array.isArray(root.documents) || root.documents.length === 0) {
    throw new Error("documents должен быть непустым списком");
  }
  const documents: ParsedKnowledgeYaml["documents"] = [];
  root.documents.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(`Документ #${index + 1}: должен быть объектом`);
    }
    const record = item as Record<string, unknown>;
    const title = record.title === undefined || record.title === null ? "" : String(record.title).trim();
    if (!title) {
      throw new Error(`Документ #${index + 1}: обязательное поле «title» пустое`);
    }
    const content = record.content === undefined || record.content === null ? "" : String(record.content);
    if (!content.trim()) {
      throw new Error(`Документ #${index + 1}: обязательное поле «content» пустое`);
    }
    const doc: ParsedKnowledgeYaml["documents"][number] = { title, content };
    if (record.description !== undefined && record.description !== null && String(record.description).trim()) {
      doc.description = String(record.description).trim();
    }
    documents.push(doc);
  });
  return { documents };
}
