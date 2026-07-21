import { StatusBadge } from "../StatusBadge";
import type { SalesPayment } from "../types";

export function PaymentsTable({ rows }: { rows: SalesPayment[] }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table payments">
      <thead>
        <tr>
          <th>ПЛАТЁЖ</th><th>ЗАКАЗ</th><th>ПРОВАЙДЕР</th><th className="numeric">СУММА</th><th>СТАТУС</th><th>МЕТОД</th><th>ДАТА</th><th>СВЕРКА</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td><span className="mono-strong">{row.id}</span></td>
            <td><span className="mono-strong">{row.order}</span></td>
            <td>{row.provider}</td>
            <td className="numeric nowrap"><strong>{row.amount}</strong></td>
            <td><StatusBadge value={row.status} /></td>
            <td className="mono-muted">{row.method}</td>
            <td className="nowrap">{row.date}</td>
            <td><span style={{ color: row.reconcile.color }}>{row.reconcile.label}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
