import { CategoryManagementDialog } from "../../shared/content-library/CategoryManagementDialog";
import {
  createPortalCategory,
  deletePortalCategory,
  updatePortalCategory,
  type PortalCategory,
} from "./model";
import { t } from "../../i18n";

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
      createLabel={t("portals.create_section")}
      deleteDescription={t("portals.section_can_only_deleted_once")}
      errorMessage={t("portals.could_not_change_sections")}
      subtitle={t("portals.section_decides_where_articles_sit")}
      title={t("portals.manage_sections")}
      onChanged={onChanged}
      onClose={onClose}
      onCreate={(input) => createPortalCategory(portalId, input)}
      onDelete={(categoryId) => deletePortalCategory(portalId, categoryId)}
      onUpdate={(categoryId, input) => updatePortalCategory(portalId, categoryId, input)}
    />
  );
}
