import { Modal } from "antd";
import { useMemo, useState } from "react";

import { Button } from "../../../shared/ui-controls";
import { CategoryManagementRow } from "./CategoryManagementRow";
import {
  buildKnowledgeCategoryTree,
  planCategoryDrop,
  type CategoryDropPosition,
  type KnowledgeCategoryNode,
} from "./knowledgeTree";
import {
  createKnowledgeCategory,
  deleteKnowledgeCategory,
  updateKnowledgeCategory,
  type KnowledgeCategory,
} from "./model";

type CategoryManagementProps = {
  categories: KnowledgeCategory[];
  onChanged: () => Promise<unknown>;
  onClose: () => void;
};

export function CategoryManagement({ categories, onChanged, onClose }: CategoryManagementProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [createParentId, setCreateParentId] = useState<number | null | undefined>();
  const [draftName, setDraftName] = useState("");
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tree = useMemo(() => buildKnowledgeCategoryTree(categories), [categories]);

  function cancelEdit() {
    setEditingId(null);
    setCreateParentId(undefined);
    setDraftName("");
  }

  function startEdit(category: KnowledgeCategoryNode) {
    setCreateParentId(undefined);
    setEditingId(category.id);
    setDraftName(category.name);
    setError(null);
  }

  function startCreate(parentId: number | null) {
    setEditingId(null);
    setCreateParentId(parentId);
    setDraftName("");
    setError(null);
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      cancelEdit();
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось изменить категории");
    } finally {
      setBusy(false);
    }
  }

  function saveEdit(category: KnowledgeCategoryNode) {
    const name = draftName.trim();
    if (!name || name === category.name) {
      cancelEdit();
      return;
    }
    void run(() => updateKnowledgeCategory(category.id, { name }));
  }

  function saveCreate() {
    const name = draftName.trim();
    if (!name || createParentId === undefined) return;
    const siblings = categories.filter((category) => category.parentId === createParentId);
    const sortOrder = Math.max(0, ...siblings.map((category) => category.sortOrder)) + 10;
    void run(() => createKnowledgeCategory({ name, parentId: createParentId, sortOrder }));
  }

  function removeCategory(category: KnowledgeCategoryNode) {
    void run(() => deleteKnowledgeCategory(category.id));
  }

  function dropCategory(targetId: number, position: CategoryDropPosition) {
    if (draggedId === null) return;
    const updates = planCategoryDrop(categories, draggedId, targetId, position);
    setDraggedId(null);
    if (updates.length === 0) return;
    void run(async () => {
      for (const update of updates) {
        await updateKnowledgeCategory(update.id, {
          parentId: update.parentId,
          sortOrder: update.sortOrder,
        });
      }
    });
  }

  return (
    <Modal
      className="knowledge-category-modal"
      destroyOnClose
      footer={(
        <div className="knowledge-category-modal-footer">
          <Button variant="secondary" icon="plus" disabled={busy} onClick={() => startCreate(null)}>Создать категорию</Button>
          <Button variant="primary" disabled={busy} onClick={onClose}>Готово</Button>
        </div>
      )}
      open
      title={(
        <div className="knowledge-category-modal-title">
          <strong>Управление категориями</strong>
          <span>Категория определяет только размещение, не доступ</span>
        </div>
      )}
      width={560}
      onCancel={onClose}
    >
      <div className="knowledge-category-manage-list" aria-busy={busy}>
        {tree.map((category) => (
          <CategoryManagementRow
            category={category}
            createParentId={createParentId}
            draftName={draftName}
            editingId={editingId}
            level={0}
            onCancelEdit={cancelEdit}
            onCreateChild={startCreate}
            onDelete={removeCategory}
            onDragStart={setDraggedId}
            onDrop={dropCategory}
            onDraftNameChange={setDraftName}
            onSaveCreate={saveCreate}
            onSaveEdit={saveEdit}
            onStartEdit={startEdit}
            key={category.id}
          />
        ))}
        {createParentId === null && (
          <div className="knowledge-category-create-row root">
            <input
              autoFocus
              placeholder="Название категории"
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") saveCreate();
                if (event.key === "Escape") {
                  event.stopPropagation();
                  cancelEdit();
                }
              }}
            />
            <button className="save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>Сохранить</button>
            <button type="button" onClick={cancelEdit}>Отмена</button>
          </div>
        )}
        {error && <div className="knowledge-category-error">{error}</div>}
      </div>
    </Modal>
  );
}
