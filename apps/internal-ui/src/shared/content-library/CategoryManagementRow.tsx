import type { DragEvent } from "react";

import { Icon } from "../icons";
import type {
  CategoryDropPosition,
  ManagedContentCategoryNode,
} from "./categoryManagementModel";

function dropPosition(event: DragEvent<HTMLDivElement>, isSystem: boolean): CategoryDropPosition {
  const bounds = event.currentTarget.getBoundingClientRect();
  const offset = (event.clientY - bounds.top) / bounds.height;
  if (offset < 0.3) return "before";
  if (offset > 0.7 || isSystem) return "after";
  return "inside";
}

export function CategoryManagementRow({
  category,
  createParentId,
  draftName,
  editingId,
  level,
  onCancel,
  onCreateChild,
  onDelete,
  onDragStart,
  onDrop,
  onDraftChange,
  onSaveCreate,
  onSaveEdit,
  onStartEdit,
}: {
  category: ManagedContentCategoryNode;
  createParentId: number | null | undefined;
  draftName: string;
  editingId: number | null;
  level: number;
  onCancel: () => void;
  onCreateChild: (categoryId: number) => void;
  onDelete: (category: ManagedContentCategoryNode) => void;
  onDragStart: (categoryId: number) => void;
  onDrop: (targetId: number, position: CategoryDropPosition) => void;
  onDraftChange: (value: string) => void;
  onSaveCreate: () => void;
  onSaveEdit: (category: ManagedContentCategoryNode) => void;
  onStartEdit: (category: ManagedContentCategoryNode) => void;
}) {
  const locked = Boolean(category.isSystem);
  const deletable = !locked && category.children.length === 0 && category.count === 0;
  const editor = (
    <div className="knowledge-category-inline-edit">
      <input autoFocus value={draftName} onChange={(event) => onDraftChange(event.target.value)} onKeyDown={(event) => {
        if (event.key === "Enter") onSaveEdit(category);
        if (event.key === "Escape") onCancel();
      }} />
      <button className="save" disabled={!draftName.trim()} type="button" onClick={() => onSaveEdit(category)}>Сохранить</button>
      <button type="button" onClick={onCancel}>Отмена</button>
    </div>
  );
  return (
    <>
      <div
        className="knowledge-category-manage-row"
        draggable={!locked && editingId !== category.id}
        style={{ paddingLeft: 10 + level * 20 }}
        onDragOver={(event) => event.preventDefault()}
        onDragStart={() => onDragStart(category.id)}
        onDrop={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDrop(category.id, dropPosition(event, locked));
        }}
      >
        {locked ? <span className="knowledge-category-drag-spacer" /> : <span className="knowledge-category-drag-handle"><Icon name="grip" size={14} /></span>}
        <Icon name={category.children.length ? "chevron" : "folder"} size={14} />
        {editingId === category.id ? editor : <>
          <button className="knowledge-category-manage-name" disabled={locked} type="button" onClick={() => onStartEdit(category)}>{category.name}</button>
          {locked && <span className="knowledge-system-badge">СИСТ.</span>}
          <span className="knowledge-category-count">{category.count}</span>
          {!locked && <button aria-label={`Создать подкатегорию в ${category.name}`} className="knowledge-category-action" type="button" onClick={() => onCreateChild(category.id)}><Icon name="plus" size={14} /></button>}
          <button aria-label={`Удалить ${category.name}`} className="knowledge-category-delete" disabled={!deletable} type="button" onClick={() => onDelete(category)}><Icon name="trash" size={14} /></button>
        </>}
      </div>
      {createParentId === category.id && (
        <div className="knowledge-category-create-row" style={{ marginLeft: 50 + level * 20 }}>
          <input autoFocus placeholder="Название категории" value={draftName} onChange={(event) => onDraftChange(event.target.value)} onKeyDown={(event) => {
            if (event.key === "Enter") onSaveCreate();
            if (event.key === "Escape") onCancel();
          }} />
          <button className="save" disabled={!draftName.trim()} type="button" onClick={onSaveCreate}>Сохранить</button>
          <button type="button" onClick={onCancel}>Отмена</button>
        </div>
      )}
      {category.children.map((child) => <CategoryManagementRow
        category={child} createParentId={createParentId} draftName={draftName}
        editingId={editingId} level={level + 1} onCancel={onCancel}
        onCreateChild={onCreateChild} onDelete={onDelete} onDragStart={onDragStart}
        onDrop={onDrop} onDraftChange={onDraftChange} onSaveCreate={onSaveCreate}
        onSaveEdit={onSaveEdit} onStartEdit={onStartEdit} key={child.id}
      />)}
    </>
  );
}
