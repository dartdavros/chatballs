import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { formatDate } from "../../../shared/utils";
import { Button } from "../../../shared/ui-controls";
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
  if (loading) return <div className="knowledge-table-state"><LoadingState variant="inline" /></div>;
  if (error) return <div className="knowledge-table-state"><strong>Не удалось загрузить знания</strong><Button variant="secondary" onClick={onRetry}>Повторить</Button></div>;
  if (items.length === 0) {
    if (selectedCategoryId !== undefined && !hasActiveFilters) {
      return (
        <div className="knowledge-empty-category">
          <span><Icon name="folder" size={24} /></span>
          <strong>В категории пока нет знаний</strong>
          <p>Создайте знание в этой категории или переместите существующие.</p>
          {canCreate && <Button variant="primary" onClick={onCreate}>Создать знание</Button>}
        </div>
      );
    }
    return <div className="knowledge-table-state"><strong>{hasActiveFilters ? "Ничего не найдено" : "Знаний пока нет"}</strong></div>;
  }

  const allVisibleSelected = items.every((item) => selectedIds.has(item.id));

  return (
    <div className="table-card knowledge-table-card">
      <table className="baseline-table knowledge-table">
        <colgroup>
          {canSelect && <col className="knowledge-col-select" />}
          <col className="knowledge-col-title" />
          <col className="knowledge-col-category" />
          <col className="knowledge-col-visibility" />
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
            <th>ДОСТУПНОСТЬ</th>
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
                  className="ai-agent-name-link"
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
              <td>
                {item.visibility === "ORGANIZATION" ? (
                  <span className="knowledge-visibility-badge organization">Организация</span>
                ) : (
                  <span className="knowledge-department-badges">
                    {item.departments.map((department) => <span key={department.id}>{department.name}</span>)}
                  </span>
                )}
              </td>
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
      {!bulkMode && <div className="ai-table-footer">
        <span>{items.length} знаний</span>
        <span>{selectedIds.size > 0 ? `Выбрано: ${selectedIds.size}` : "Изменения знаний применяются к агентам сразу"}</span>
      </div>}
    </div>
  );
}
