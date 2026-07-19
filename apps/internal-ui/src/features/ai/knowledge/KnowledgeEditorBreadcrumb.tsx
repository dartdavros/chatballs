import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory } from "./types";

export function KnowledgeEditorBreadcrumb({
  categories,
  categoryId,
  title,
  onBack,
}: {
  categories: KnowledgeCategory[];
  categoryId: number | null;
  title: string;
  onBack: () => void;
}) {
  const category = categoryId === null ? "" : knowledgeCategoryPath(categories, categoryId);
  return (
    <div className="knowledge-editor-breadcrumb">
      <button type="button" onClick={onBack}>Знания</button>
      {category && <><span>/</span><em>{category}</em></>}
      <span>/</span><strong>{title || "Создание знания"}</strong>
    </div>
  );
}
