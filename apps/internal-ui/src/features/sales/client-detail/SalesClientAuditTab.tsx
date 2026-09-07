import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";

export function SalesClientAuditTab({ audit }: { audit: ClientDetailVm["audit"] }) {
  if (audit.length === 0) return <EmptyState title="Пока нет событий" />;
  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table">
        <thead>
          <tr>
            <th>Время</th>
            <th>Действие</th>
            <th>Объект</th>
            <th>Сотрудник</th>
            <th>Результат</th>
          </tr>
        </thead>
        <tbody>
          {audit.map((item, index) => (
            <tr key={`${item.time}-${item.action}-${index}`}>
              <td>{item.time}</td>
              <td>{item.action}</td>
              <td>{item.object}</td>
              <td>{item.actor}</td>
              <td>{item.result}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
