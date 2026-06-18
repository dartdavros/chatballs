import type { salesClientDetail } from "./model";

type Order = typeof salesClientDetail.orders[number];

export function SalesClientOrdersTab({ orders }: { orders: Order[] }) {
  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table">
        <thead>
          <tr>
            <th>ЗАКАЗ</th>
            <th>ДАТА</th>
            <th>ПРОДУКТ / OFFER</th>
            <th className="numeric">СУММА</th>
            <th>ОПЛАТА</th>
            <th>ИСПОЛНЕНИЕ</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td><a href="#" onClick={(event) => event.preventDefault()}>{order.id}</a></td>
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
