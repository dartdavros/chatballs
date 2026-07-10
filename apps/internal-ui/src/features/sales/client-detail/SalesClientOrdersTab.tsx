import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";

export function SalesClientOrdersTab({ orders }: { orders: ClientDetailVm["orders"] }) {
  if (orders.length === 0) return <EmptyState title="У контакта ещё нет заказов" />;
  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table">
        <thead>
          <tr>
            <th>ЗАКАЗ</th>
            <th>ДАТА</th>
            <th>ПРОДУКТ</th>
            <th className="numeric">СУММА</th>
            <th>ОПЛАТА</th>
            <th>ИСПОЛНЕНИЕ</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td><code>{order.code}</code></td>
              <td>{order.date}</td>
              <td>{order.product}</td>
              <td className="numeric"><strong>{order.amount}</strong></td>
              <td><span>{order.payment}</span></td>
              <td><span>{order.fulfillment}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
