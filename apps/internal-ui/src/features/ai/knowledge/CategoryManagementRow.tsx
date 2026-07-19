import type { DragEvent } from "react";

import { Icon } from "../../../shared/icons";
import type { CategoryDropPosition, KnowledgeCategoryNode } from "./knowledgeTree";

type CategoryManagementRowProps = {
  category: KnowledgeCategoryNode;
  createParentId: number | null | undefined;
  draftName: string;
  editingId: number | null;
  level: number;
  onCancelEdit: () => void;
  onCreateChild: (categoryId: number) => void;
  onDelete: (category: KnowledgeCategoryNode) => void;
  onDragStart: (categoryId: number) => void;
  onDrop: (targetId: number, position: CategoryDropPosition) => void;
  onDraftNameChange: (value: string) => void;
  onSaveEdit: (category: KnowledgeCategoryNode) => void;
  onSaveCreate: () => void;
  onStartEdit: (category: KnowledgeCategoryNode) => void;
};

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
  onCancelEdit,
  onCreateChild,
  onDelete,
  onDragStart,
  onDrop,
  onDraftNameChange,
  onSaveEdit,
  onSaveCreate,
  onStartEdit,
}: CategoryManagementRowProps) {
  const hasChildren = category.children.length > 0;
  const deletable = !category.isSystem && !hasChildren && category.knowledgeCount === 0;

  return (
    <>
      <div
        className="knowledge-category-manage-row"
        draggable={!category.isSystem && editingId !== category.id}
        style={{ paddingLeft: 10 + level * 20 }}
        onDragOver={(event) => event.preventDefault()}
        onDragStart={() => onDragStart(category.id)}
        onDrop={(event) => {
          event.preventDefault();
          event.stopPropagation();
          onDrop(category.id, dropPosition(event, category.isSystem));
        }}
      >
        {category.isSystem ? <span className="knowledge-category-drag-spacer" /> : (
          <span className="knowledge-category-drag-handle" title="Перетащите для перемещения">
            <Icon name="grip" size={14} />
          </span>
        )}
        {hasChildren ? <Icon name="chevron" size={14} /> : <Icon name="folder" size={15} />}
        {editingId === category.id ? (
          <div className="knowledge-category-inline-edit">
            <input
              autoFocus
              value={draftName}
              onChange={(event) => onDraftNameChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") onSaveEdit(category);
                if (event.key === "Escape") {
                  event.stopPropagation();
                  onCancelEdit();
                }
              }}
            />
            <button className="save" disabled={!draftName.trim()} type="button" onClick={() => onSaveEdit(category)}>Сохранить</button>
            <button type="button" onClick={onCancelEdit}>Отмена</button>
          </div>
        ) : (
          <>
            <button
              className="knowledge-category-manage-name"
              disabled={category.isSystem}
              title={category.isSystem ? "Системная категория — нельзя изменить" : "Переименовать"}
              type="button"
              onClick={() => onStartEdit(category)}
            >
              {category.name}
            </button>
            {category.isSystem && <span className="knowledge-system-badge">СИСТ.</span>}
            <span className="knowledge-category-count">{category.knowledgeCount ?? 0}</span>
            {!category.isSystem && (
              <button aria-label={`Создать подкатегорию в ${category.name}`} className="knowledge-category-action" type="button" onClick={() => onCreateChild(category.id)}>
                <Icon name="plus" size={14} />
              </button>
            )}
            <button
              aria-label={`Удалить ${category.name}`}
              className="knowledge-category-delete"
              disabled={!deletable}
              title={!deletable ? "Можно удалить только пустую категорию без вложенных категорий" : "Удалить"}
              type="button"
              onClick={() => onDelete(category)}
            >
              <Icon name="trash" size={14} />
            </button>
          </>
        )}
      </div>
      {createParentId === category.id && (
        <div className="knowledge-category-create-row" style={{ marginLeft: 50 + level * 20 }}>
          <input
            autoFocus
            placeholder="Название категории"
            value={draftName}
            onChange={(event) => onDraftNameChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSaveCreate();
              if (event.key === "Escape") {
                event.stopPropagation();
                onCancelEdit();
              }
            }}
          />
          <button className="save" disabled={!draftName.trim()} type="button" onClick={onSaveCreate}>Сохранить</button>
          <button type="button" onClick={onCancelEdit}>Отмена</button>
        </div>
      )}
      {category.children.map((child) => (
        <CategoryManagementRow
          category={child}
          createParentId={createParentId}
          draftName={draftName}
          editingId={editingId}
          level={level + 1}
          onCancelEdit={onCancelEdit}
          onCreateChild={onCreateChild}
          onDelete={onDelete}
          onDragStart={onDragStart}
          onDrop={onDrop}
          onDraftNameChange={onDraftNameChange}
          onSaveEdit={onSaveEdit}
          onSaveCreate={onSaveCreate}
          onStartEdit={onStartEdit}
          key={child.id}
        />
      ))}
    </>
  );
}
