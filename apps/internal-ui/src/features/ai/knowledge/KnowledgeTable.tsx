import { Icon } from "../../../shared/icons";
import { EmptyState, StatusPill } from "../../../shared/ui";
import { formatDate } from "../../../shared/utils";
import { formatSize, type KnowledgeItem } from "./model";

type KnowledgeTableProps = {
  items: KnowledgeItem[];
  error: boolean;
  query: string;
  openKnowledge: (knowledgeId: number) => void;
};

export function KnowledgeTable({
  items,
  error,
  query,
  openKnowledge,
}: KnowledgeTableProps) {
  if (error) return <EmptyState title="Не удалось загрузить знания" />;
  if (items.length === 0) {
    return <EmptyState title={query ? "Ничего не найдено" : "Знаний пока нет"} />;
  }

  return (
    <div className="table-card">
      <table className="baseline-table">
        <thead>
          <tr>
            <th>ЗНАНИЕ</th>
            <th className="numeric">ВЛОЖЕНИЯ</th>
            <th className="numeric">АГЕНТЫ</th>
            <th>СТАТУС</th>
            <th>ОБНОВЛЕНО</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="knowledge-row" onClick={() => openKnowledge(item.id)}>
              <td>
                <div className="product-cell">
                  <span className="product-icon knowledge-icon"><Icon name="list" size={19} /></span>
                  <span>
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
                    <small>{item.description || "—"}</small>
                  </span>
                </div>
              </td>
              <td className="numeric">
                {item.attachments.length > 0
                  ? `${item.attachments.length} · ${formatSize(item.attachments.reduce((sum, attachment) => sum + attachment.size, 0))}`
                  : <span className="product-empty-value">—</span>}
              </td>
              <td className="numeric">
                {item.agentsCount || <span className="product-empty-value">—</span>}
              </td>
              <td><StatusPill status={item.isEnabled ? "active" : "disabled"} /></td>
              <td>{formatDate(item.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="ai-table-footer">
        <span>{items.length} знаний</span>
        <span>Изменения знаний применяются к агентам сразу</span>
      </div>
    </div>
  );
}
