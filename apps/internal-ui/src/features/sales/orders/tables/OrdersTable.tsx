import { Icon } from "../../../../shared/icons";
import { MonoLink, StatusBadge } from "../StatusBadge";
import type { SalesOrder } from "../types";

export function OrdersTable({ rows, openOrder }: { rows: Array<SalesOrder & { orderId: number }>; openOrder: (id: number) => void }) {
  if (rows.length === 0) return null;
  return (
    <table className="sales-orders-table orders">
      <thead>
        <tr>
          <th>ЗАКАЗ</th><th>ДАТА</th><th>КЛИЕНТ</th><th>ПРОДУКТ / OFFER</th><th className="numeric">СУММА</th>
          <th>ОПЛАТА</th><th>ИСПОЛНЕНИЕ</th><th>ИСТОЧНИК</th><th>ПРОДАВЕЦ</th><th />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td><MonoLink onClick={() => openOrder(row.orderId)}>{row.id}</MonoLink></td>
            <td className="nowrap">{row.date}</td>
            <td className="strong-text">{row.client}</td>
            <td>{row.offer}</td>
            <td className="numeric nowrap"><strong>{row.amount}</strong></td>
            <td><StatusBadge value={row.pay} /></td>
            <td><StatusBadge value={row.fulfillment} /></td>
            <td><span className="sales-orders-source"><i style={{ background: row.source.color }} />{row.source.label}</span></td>
            <td><span className={row.sellerAI ? "seller-ai" : "seller"}>{row.seller}</span></td>
            <td className="row-actions"><button type="button" aria-label="Открыть карточку заказа" onClick={() => openOrder(row.orderId)}><Icon name="more" size={17} /></button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
