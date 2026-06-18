import type { salesClientDetail } from "./model";

type AuditItem = typeof salesClientDetail.audit[number];

export function SalesClientAuditTab({ audit }: { audit: AuditItem[] }) {
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
          {audit.map((item) => (
            <tr key={`${item.time}-${item.action}`}>
              <td>{item.time}</td>
              <td>{item.action}</td>
              <td><code>{item.object}</code></td>
              <td className={`${item.ai ? "ai" : ""} ${item.muted ? "muted" : ""}`}>{item.actor}</td>
              <td><span>{item.result}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
