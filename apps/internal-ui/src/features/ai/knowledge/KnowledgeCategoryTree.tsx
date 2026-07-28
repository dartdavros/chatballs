import { CategoryTree } from "../../../shared/content-library/CategoryTree";
import type { KnowledgeCategory } from "./types";

export function KnowledgeCategoryTree({
  canManage,
  categories,
  error,
  loading,
  onManage,
  onRetry,
  onSelect,
  selectedId,
}: {
  canManage: boolean;
  categories: KnowledgeCategory[];
  error: boolean;
  loading: boolean;
  onManage: () => void;
  onRetry: () => void;
  onSelect: (categoryId: number | undefined) => void;
  selectedId?: number;
}) {
  return (
    <CategoryTree
      allLabel="Все знания"
      canManage={canManage}
      categories={categories.map((category) => ({
        id: category.id,
        name: category.name,
        parentId: category.parentId,
        count: category.knowledgeCount ?? 0,
        badge: category.isSystem ? "СИСТ." : undefined,
      }))}
      error={error}
      loading={loading}
      selectedId={selectedId}
      onManage={onManage}
      onRetry={onRetry}
      onSelect={onSelect}
    />
  );
}
