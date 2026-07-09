import { load as parseYaml } from "js-yaml";

import type { ImportDocInput } from "./docApi";

export type ParsedDocYaml = {
  product: string | null;
  documents: ImportDocInput[];
};

const REQUIRED_FIELDS = ["code", "title", "category", "content"] as const;

// Парсит YAML импорта знаний/инструкций и структурно валидирует.
// Бросает Error с человекочитаемым сообщением при невалидном YAML или структуре.
export function parseDocYaml(text: string): ParsedDocYaml {
  let data: unknown;
  try {
    data = parseYaml(text);
  } catch (error) {
    throw new Error(error instanceof Error ? `Невалидный YAML: ${error.message}` : "Невалидный YAML");
  }
  if (!data || typeof data !== "object") {
    throw new Error("Ожидается объект верхнего уровня с ключом documents");
  }
  const root = data as { product?: unknown; documents?: unknown };
  const product = root.product === undefined || root.product === null ? null : String(root.product).trim();
  if (product && !/^[a-z0-9-]+$/i.test(product)) {
    throw new Error(`product должен быть ASCII-slug, получено: «${product}»`);
  }
  if (!Array.isArray(root.documents) || root.documents.length === 0) {
    throw new Error("documents должен быть непустым списком");
  }
  const documents: ImportDocInput[] = [];
  root.documents.forEach((item, index) => {
    if (!item || typeof item !== "object") {
      throw new Error(`Документ #${index + 1}: должен быть объектом`);
    }
    const record = item as Record<string, unknown>;
    for (const field of REQUIRED_FIELDS) {
      const value = record[field];
      if (value === undefined || value === null || String(value).trim() === "") {
        throw new Error(`Документ #${index + 1}: обязательное поле «${field}» пустое`);
      }
    }
    const doc: ImportDocInput = {
      code: String(record.code).trim(),
      title: String(record.title).trim(),
      category: String(record.category).trim(),
      content: String(record.content),
    };
    if (record.inclusionMode !== undefined && record.inclusionMode !== null) {
      const inclusion = String(record.inclusionMode).trim();
      if (inclusion !== "MANDATORY" && inclusion !== "RETRIEVAL") {
        throw new Error(`Документ #${index + 1}: inclusionMode должен быть MANDATORY или RETRIEVAL`);
      }
      doc.inclusionMode = inclusion;
    }
    documents.push(doc);
  });
  return { product: product || null, documents };
}
