import { Modal } from "antd";
import { useMemo, useState } from "react";

import { DecisionDialog } from "../DecisionDialog";
import { Button } from "../ui-controls";
import { CategoryManagementRow } from "./CategoryManagementRow";
import {
  buildCategoryTree,
  planCategoryDrop,
  type CategoryDropPosition,
  type ManagedContentCategory,
  type ManagedContentCategoryNode,
} from "./categoryManagementModel";

export type CategoryMutation = {
  name?: string;
  parentId?: number | null;
  sortOrder?: number;
};

export function CategoryManagementDialog({
  categories,
  createLabel = "Создать категорию",
  deleteDescription = "Категорию можно удалить только после переноса вложенных категорий и материалов.",
  errorMessage = "Не удалось изменить категории",
  onChanged,
  onClose,
  onCreate,
  onDelete,
  onUpdate,
  subtitle = "Категория определяет только размещение, не доступ",
  title = "Управление категориями",
}: {
  categories: ManagedContentCategory[];
  createLabel?: string;
  deleteDescription?: string;
  errorMessage?: string;
  onChanged: () => Promise<unknown>;
  onClose: () => void;
  onCreate: (input: Required<Pick<CategoryMutation, "name" | "parentId" | "sortOrder">>) => Promise<unknown>;
  onDelete: (categoryId: number) => Promise<unknown>;
  onUpdate: (categoryId: number, input: CategoryMutation) => Promise<unknown>;
  subtitle?: string;
  title?: string;
}) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [createParentId, setCreateParentId] = useState<number | null | undefined>();
  const [draftName, setDraftName] = useState("");
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<ManagedContentCategoryNode | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const tree = useMemo(() => buildCategoryTree(categories), [categories]);

  function cancel() {
    setEditingId(null);
    setCreateParentId(undefined);
    setDraftName("");
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      cancel();
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : errorMessage);
    } finally {
      setBusy(false);
    }
  }

  function saveCreate() {
    const name = draftName.trim();
    if (!name || createParentId === undefined) return;
    const siblings = categories.filter((item) => item.parentId === createParentId);
    const sortOrder = Math.max(0, ...siblings.map((item) => item.sortOrder)) + 10;
    void run(() => onCreate({ name, parentId: createParentId, sortOrder }));
  }

  function drop(targetId: number, position: CategoryDropPosition) {
    if (draggedId === null) return;
    const updates = planCategoryDrop(categories, draggedId, targetId, position);
    setDraggedId(null);
    if (!updates.length) return;
    void run(async () => {
      for (const update of updates) {
        await onUpdate(update.id, { parentId: update.parentId, sortOrder: update.sortOrder });
      }
    });
  }

  return (
    <>
      <Modal
        className="content-category-modal"
        destroyOnHidden
        footer={<div className="content-category-modal-footer"><Button variant="secondary" icon="plus" disabled={busy} onClick={() => { setEditingId(null); setCreateParentId(null); setDraftName(""); }}>{createLabel}</Button><Button variant="primary" disabled={busy} onClick={onClose}>Готово</Button></div>}
        open title={<div className="content-category-modal-title"><strong>{title}</strong><span>{subtitle}</span></div>}
        width={560} onCancel={onClose}
      >
        <div className="content-category-list" aria-busy={busy}>
          {tree.map((category) => <CategoryManagementRow
            category={category} createParentId={createParentId} draftName={draftName}
            editingId={editingId} level={0} onCancel={cancel}
            onCreateChild={(id) => { setEditingId(null); setCreateParentId(id); setDraftName(""); }}
            onDelete={setDeleting} onDragStart={setDraggedId} onDrop={drop}
            onDraftChange={setDraftName} onSaveCreate={saveCreate}
            onSaveEdit={(item) => {
              const name = draftName.trim();
              if (!name || name === item.name) cancel();
              else void run(() => onUpdate(item.id, { name }));
            }}
            onStartEdit={(item) => { setCreateParentId(undefined); setEditingId(item.id); setDraftName(item.name); }}
            key={category.id}
          />)}
          {createParentId === null && <div className="content-category-create root">
            <input autoFocus placeholder="Название категории" value={draftName} onChange={(event) => setDraftName(event.target.value)} onKeyDown={(event) => {
              if (event.key === "Enter") saveCreate();
              if (event.key === "Escape") cancel();
            }} />
            <button className="save" disabled={!draftName.trim()} type="button" onClick={saveCreate}>Сохранить</button>
            <button type="button" onClick={cancel}>Отмена</button>
          </div>}
          {error && <div className="content-category-error">{error}</div>}
        </div>
      </Modal>
      <DecisionDialog
        open={Boolean(deleting)} onClose={() => setDeleting(null)} tone="danger" icon="trash"
        title="Удалить категорию?" description={deleteDescription}
        actions={<><Button variant="secondary" onClick={() => setDeleting(null)}>Отмена</Button><Button variant="danger-outline" disabled={busy} onClick={() => {
          if (!deleting) return;
          const id = deleting.id;
          setDeleting(null);
          void run(() => onDelete(id));
        }}>Удалить</Button></>}
      />
    </>
  );
}
