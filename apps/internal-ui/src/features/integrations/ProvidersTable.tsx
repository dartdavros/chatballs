import { PROVIDERS, type Integration } from "./model";
import { ConnectionIcon, RowActions, StatusCell } from "./rows";

type ProvidersTableProps = {
  items: Integration[];
  testingId: number | null;
  onTest: (integration: Integration) => void;
  onEdit: (integration: Integration) => void;
  onDelete: (integration: Integration) => void;
};

export function ProvidersTable({ items, testingId, onTest, onEdit, onDelete }: ProvidersTableProps) {
  return (
    <div className="table-card">
      <table className="baseline-table">
        <thead>
          <tr>
            <th>НАЗВАНИЕ</th>
            <th>СЕКРЕТ</th>
            <th>КОНФИГ</th>
            <th>СТАТУС</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const meta = PROVIDERS[item.provider];
            return (
              <tr key={item.id}>
                <td>
                  <div className="product-cell">
                    <ConnectionIcon provider={item.provider} />
                    <span><strong>{item.name}</strong><small>{meta.label}</small></span>
                  </div>
                </td>
                <td>{item.hasSecret ? <code className="ai-mono">••••••••</code> : <span className="product-empty-value">—</span>}</td>
                <td className="integration-config">
                  <span>{item.config.baseUrl || meta.defaultBaseUrl || "—"}</span>
                  {item.config.defaultModel && <small>{item.config.defaultModel}</small>}
                </td>
                <td><StatusCell integration={item} /></td>
                <td className="row-actions">
                  <RowActions integration={item} testing={testingId === item.id} onTest={onTest} onEdit={onEdit} onDelete={onDelete} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
