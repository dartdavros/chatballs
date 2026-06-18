import { StatusBadge } from "../StatusBadge";
import type { SalesRefund } from "../types";

export function RefundsTable({ rows }: { rows: SalesRefund[] }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table refunds">
      <thead>
        <tr>
          <th>ВОЗВРАТ</th><th>ЗАКАЗ / ПЛАТЁЖ</th><th className="numeric">СУММА</th><th>ПРИЧИНА</th><th>СТАТУС</th><th>ИНИЦИАТОР</th><th>ДАТА</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td><span className="mono-strong">{row.id}</span></td>
            <td className="mono-muted">{row.reference}</td>
            <td className="numeric nowrap"><strong>{row.amount}</strong></td>
            <td>{row.reason}</td>
            <td><StatusBadge value={row.status} /></td>
            <td>{row.actor}</td>
            <td className="nowrap">{row.date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
