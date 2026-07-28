import { ContentEditorBreadcrumb } from "../../../shared/content-library/ContentEditorBreadcrumb";
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
    <ContentEditorBreadcrumb
      backLabel="Знания"
      category={category}
      title={title || "Создание знания"}
      onBack={onBack}
    />
  );
}
