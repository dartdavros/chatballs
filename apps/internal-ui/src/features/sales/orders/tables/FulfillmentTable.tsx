import { Icon } from "../../../../shared/icons";
import { StatusBadge } from "../StatusBadge";
import type { SalesFulfillment } from "../types";

export function FulfillmentTable({ rows }: { rows: SalesFulfillment[] }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table fulfillment">
      <thead>
        <tr>
          <th>ЗАКАЗ</th><th>ПРОДУКТ</th><th>ОПЕРАЦИЯ</th><th>СТАТУС</th><th className="numeric">ПОПЫТКИ</th><th>ПОСЛ. ОШИБКА</th><th>ОБНОВЛЕНО</th><th className="numeric">ДЕЙСТВИЕ</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.operation}>
            <td><span className="mono-strong">{row.order}</span></td>
            <td>{row.product}</td>
            <td className="mono-muted">{row.operation}</td>
            <td><StatusBadge value={row.status} /></td>
            <td className={`numeric attempts ${row.attention ? "danger" : ""}`}>{row.attempts}</td>
            <td className={`mono-muted ${row.attention ? "error" : ""}`}>{row.error}</td>
            <td className="nowrap">{row.updated}</td>
            <td className="numeric">{row.attention ? <button className="sales-orders-retry" type="button"><Icon name="refresh" size={14} />Сверка</button> : <span className="muted-dash">—</span>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
