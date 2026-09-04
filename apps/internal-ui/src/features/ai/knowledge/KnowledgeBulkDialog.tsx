import { Modal } from "antd";

import { Button } from "../../../shared/ui-controls";
import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory } from "./types";

export function KnowledgeBulkDialog({
  busy,
  categories,
  categoryId,
  error,
  onCancel,
  onCategoryChange,
  onSubmit,
}: {
  busy: boolean;
  categories: KnowledgeCategory[];
  categoryId: number | null;
  error: string | null;
  onCancel: () => void;
  onCategoryChange: (categoryId: number | null) => void;
  onSubmit: () => void;
}) {
  return (
    <Modal className="knowledge-bulk-modal" open title="Переместить в категорию" onCancel={onCancel} footer={null} destroyOnClose>
      <div className="knowledge-bulk-dialog-body">
        <label className="knowledge-editor-field knowledge-category-select">
          <span>Категория</span>
          <div>
            <select disabled={busy} value={categoryId ?? ""} onChange={(event) => onCategoryChange(event.target.value ? Number(event.target.value) : null)}>
              <option value="">Выберите категорию</option>
              {categories.map((category) => <option value={category.id} key={category.id}>{knowledgeCategoryPath(categories, category.id) || category.name}</option>)}
            </select>
          </div>
        </label>
        {error && <div className="knowledge-editor-error">{error}</div>}
        <div className="knowledge-bulk-dialog-actions">
          <Button variant="secondary" disabled={busy} onClick={onCancel}>Отмена</Button>
          <Button variant="primary" disabled={busy} onClick={onSubmit}>Применить</Button>
        </div>
      </div>
    </Modal>
  );
}
