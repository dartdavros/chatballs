import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";

export function SalesClientAuditTab({ audit }: { audit: ClientDetailVm["audit"] }) {
  if (audit.length === 0) return <EmptyState title="Аудит-событий пока нет" />;
  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table audit">
        <thead>
          <tr>
            <th>ВРЕМЯ</th>
            <th>ДЕЙСТВИЕ</th>
            <th>ОБЪЕКТ</th>
            <th>АКТОР</th>
            <th>РЕЗУЛЬТАТ</th>
          </tr>
        </thead>
        <tbody>
          {audit.map((item, index) => (
            <tr key={`${item.time}-${item.action}-${index}`}>
              <td>{item.time}</td>
              <td>{item.action}</td>
              <td><code>{item.object}</code></td>
              <td>{item.actor}</td>
              <td><span>{item.result}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
