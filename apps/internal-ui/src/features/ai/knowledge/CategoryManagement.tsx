import { CategoryManagementDialog } from "../../../shared/content-library/CategoryManagementDialog";
import {
  createKnowledgeCategory,
  deleteKnowledgeCategory,
  updateKnowledgeCategory,
  type KnowledgeCategory,
} from "./model";

export function CategoryManagement({
  categories,
  onChanged,
  onClose,
}: {
  categories: KnowledgeCategory[];
  onChanged: () => Promise<unknown>;
  onClose: () => void;
}) {
  return (
    <CategoryManagementDialog
      categories={categories.map((item) => ({
        id: item.id,
        name: item.name,
        parentId: item.parentId,
        sortOrder: item.sortOrder,
        count: item.knowledgeCount ?? 0,
        isSystem: item.isSystem,
      }))}
      onChanged={onChanged}
      onClose={onClose}
      onCreate={createKnowledgeCategory}
      onDelete={deleteKnowledgeCategory}
      onUpdate={updateKnowledgeCategory}
    />
  );
}
