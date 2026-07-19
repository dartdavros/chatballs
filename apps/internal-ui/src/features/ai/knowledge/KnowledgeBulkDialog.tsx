import { Modal } from "antd";

import { Button } from "../../../shared/ui-controls";
import { KnowledgeDepartmentPicker } from "./KnowledgeDepartmentPicker";
import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory, KnowledgeDepartmentReference, KnowledgeVisibility } from "./types";

export type KnowledgeBulkMode = "departments" | "move" | "visibility";

export function KnowledgeBulkDialog({
  busy,
  categories,
  categoryId,
  departmentIds,
  departments,
  error,
  mode,
  visibility,
  onCancel,
  onCategoryChange,
  onDepartmentChange,
  onSubmit,
  onVisibilityChange,
}: {
  busy: boolean;
  categories: KnowledgeCategory[];
  categoryId: number | null;
  departmentIds: number[];
  departments: KnowledgeDepartmentReference[];
  error: string | null;
  mode: KnowledgeBulkMode;
  visibility: KnowledgeVisibility;
  onCancel: () => void;
  onCategoryChange: (categoryId: number | null) => void;
  onDepartmentChange: (departmentIds: number[]) => void;
  onSubmit: () => void;
  onVisibilityChange: (visibility: KnowledgeVisibility) => void;
}) {
  const title = mode === "move" ? "Переместить в категорию" : mode === "visibility" ? "Изменить доступность" : "Заменить отделы";
  return (
    <Modal className="knowledge-bulk-modal" open title={title} onCancel={onCancel} footer={null} destroyOnClose>
      <div className="knowledge-bulk-dialog-body">
        {mode === "move" ? (
          <label className="knowledge-editor-field knowledge-category-select">
            <span>Категория</span>
            <div>
              <select disabled={busy} value={categoryId ?? ""} onChange={(event) => onCategoryChange(event.target.value ? Number(event.target.value) : null)}>
                <option value="">Выберите категорию</option>
                {categories.map((category) => <option value={category.id} key={category.id}>{knowledgeCategoryPath(categories, category.id) || category.name}</option>)}
              </select>
            </div>
          </label>
        ) : (
          <>
            {mode === "visibility" && (
              <div className="knowledge-editor-field">
                <span>Область доступности</span>
                <div className="knowledge-visibility-segmented">
                  <button className={visibility === "ORGANIZATION" ? "active" : ""} disabled={busy} type="button" onClick={() => onVisibilityChange("ORGANIZATION")}>Организация</button>
                  <button className={visibility === "DEPARTMENTS" ? "active" : ""} disabled={busy} type="button" onClick={() => onVisibilityChange("DEPARTMENTS")}>Отделы</button>
                </div>
              </div>
            )}
            {(mode === "departments" || visibility === "DEPARTMENTS") && (
              <KnowledgeDepartmentPicker departments={departments} disabled={busy} selectedIds={departmentIds} onChange={onDepartmentChange} />
            )}
          </>
        )}
        {error && <div className="knowledge-editor-error">{error}</div>}
        <div className="knowledge-bulk-dialog-actions">
          <Button variant="secondary" disabled={busy} onClick={onCancel}>Отмена</Button>
          <Button variant="primary" disabled={busy} onClick={onSubmit}>Применить</Button>
        </div>
      </div>
    </Modal>
  );
}
