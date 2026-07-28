import { CategoryManagementDialog } from "../../shared/content-library/CategoryManagementDialog";
import {
  createPortalCategory,
  deletePortalCategory,
  updatePortalCategory,
  type PortalCategory,
} from "./model";

export function PortalCategoryManagement({
  categories,
  onChanged,
  onClose,
  portalId,
}: {
  categories: PortalCategory[];
  onChanged: () => Promise<void>;
  onClose: () => void;
  portalId: number;
}) {
  return (
    <CategoryManagementDialog
      categories={categories.map((item) => ({
        id: item.id,
        name: item.name,
        parentId: item.parentId,
        sortOrder: item.sortOrder,
        count: item.articleCount,
      }))}
      createLabel="Создать раздел"
      deleteDescription="Раздел можно удалить только после переноса вложенных разделов и статей."
      errorMessage="Не удалось изменить разделы"
      subtitle="Раздел определяет расположение статей в публичном портале"
      title="Управление разделами"
      onChanged={onChanged}
      onClose={onClose}
      onCreate={(input) => createPortalCategory(portalId, input)}
      onDelete={(categoryId) => deletePortalCategory(portalId, categoryId)}
      onUpdate={(categoryId, input) => updatePortalCategory(portalId, categoryId, input)}
    />
  );
}
