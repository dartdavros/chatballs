import { ContentLibraryTable } from "../../../shared/content-library/ContentLibraryTable";
import { formatDate } from "../../../shared/utils";
import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory, KnowledgeItem } from "./model";

type KnowledgeTableProps = {
  bulkMode: boolean;
  canCreate: boolean;
  canSelect: boolean;
  categories: KnowledgeCategory[];
  items: KnowledgeItem[];
  error: boolean;
  hasActiveFilters: boolean;
  loading: boolean;
  onCreate: () => void;
  onRetry: () => void;
  onToggleSelected: (knowledgeId: number) => void;
  onToggleVisible: () => void;
  openKnowledge: (knowledgeId: number) => void;
  selectedCategoryId?: number;
  selectedIds: Set<number>;
};

export function KnowledgeTable({
  bulkMode,
  canCreate,
  canSelect,
  categories,
  items,
  error,
  hasActiveFilters,
  loading,
  onCreate,
  onRetry,
  onToggleSelected,
  onToggleVisible,
  openKnowledge,
  selectedCategoryId,
  selectedIds,
}: KnowledgeTableProps) {
  const allVisibleSelected = items.every((item) => selectedIds.has(item.id));
  const emptyCategory = selectedCategoryId !== undefined && !hasActiveFilters;

  return (
    <ContentLibraryTable
      canCreate={canCreate && emptyCategory}
      createLabel="Создать знание"
      emptyDescription={emptyCategory ? "Создайте знание в этой категории или переместите существующие." : undefined}
      emptyTitle={emptyCategory ? "В категории пока нет знаний" : hasActiveFilters ? "Ничего не найдено" : "Знаний пока нет"}
      error={error}
      errorTitle="Не удалось загрузить знания"
      hasItems={items.length > 0}
      loading={loading}
      onCreate={onCreate}
      onRetry={onRetry}
      footer={!bulkMode && <div className="ai-table-footer">
        <span>{items.length} знаний</span>
        <span>{selectedIds.size > 0 ? `Выбрано: ${selectedIds.size}` : "Изменения знаний применяются к агентам сразу"}</span>
      </div>}
    >
      <table className="baseline-table knowledge-table">
        <colgroup>
          {canSelect && <col className="knowledge-col-select" />}
          <col className="knowledge-col-title" />
          <col className="knowledge-col-category" />
          {!bulkMode && <col className="knowledge-col-attachments" />}
          {!bulkMode && <col className="knowledge-col-agents" />}
          <col className="knowledge-col-status" />
          <col className="knowledge-col-updated" />
        </colgroup>
        <thead>
          <tr>
            {canSelect && (
              <th className="knowledge-select-cell">
                <input aria-label="Выбрать все знания" checked={allVisibleSelected} type="checkbox" onChange={onToggleVisible} />
              </th>
            )}
            <th>ЗНАНИЕ</th>
            <th>КАТЕГОРИЯ</th>
            {!bulkMode && <th className="numeric">ВЛОЖ.</th>}
            {!bulkMode && <th className="numeric">АГЕНТЫ</th>}
            <th>СТАТУС</th>
            <th>ОБНОВЛЕНО</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className={`knowledge-row${selectedIds.has(item.id) ? " selected" : ""}`} onClick={() => openKnowledge(item.id)}>
              {canSelect && (
                <td className="knowledge-select-cell" onClick={(event) => event.stopPropagation()}>
                  <input
                    aria-label={`Выбрать ${item.title}`}
                    checked={selectedIds.has(item.id)}
                    type="checkbox"
                    onChange={() => onToggleSelected(item.id)}
                  />
                </td>
              )}
              <td>
                <button
                  className="link is-strong is-neutral"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    openKnowledge(item.id);
                  }}
                >
                  {item.title}
                </button>
                <small className="knowledge-description">{item.description || "—"}</small>
              </td>
              <td className="knowledge-category-path">{knowledgeCategoryPath(categories, item.category.id) || item.category.name}</td>
              {!bulkMode && <td className="numeric">
                {item.attachments.length || <span className="product-empty-value">—</span>}
              </td>}
              {!bulkMode && <td className="numeric">
                {item.agentsCount || <span className="product-empty-value">—</span>}
              </td>}
              <td><span className={`knowledge-status ${item.isEnabled ? "active" : "disabled"}`}><i />{item.isEnabled ? "Активно" : "Выключено"}</span></td>
              <td>{formatDate(item.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ContentLibraryTable>
  );
}
