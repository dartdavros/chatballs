import { OrderDetailCard, OrderDetailCardTitle } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderPaymentsTab({ order }: { order: OrderDetail }) {
  return (
    <div className="order-detail-tab-stack">
      <OrderDetailCard className="order-detail-table-card">
        <OrderDetailCardTitle>Платежи и попытки</OrderDetailCardTitle>
        <table className="order-detail-table">
          <thead>
            <tr><th>ПЛАТЁЖ</th><th>ПРОВАЙДЕР</th><th className="numeric">СУММА</th><th>МЕТОД</th><th>СТАТУС</th><th>СВЕРКА</th></tr>
          </thead>
          <tbody>
            {order.payments.rows.map((payment) => (
              <tr key={payment.id}>
                <td><b className="mono">{payment.id}</b></td>
                <td>{payment.provider}</td>
                <td className="numeric"><b>{payment.amount}</b></td>
                <td><span className="mono">{payment.method}</span></td>
                <td><span className="order-detail-small-success">{payment.status}</span></td>
                <td><span className="success-text">{payment.reconcile}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </OrderDetailCard>
      <OrderDetailCard className="order-detail-provider-events">
        <OrderDetailCardTitle>События провайдера</OrderDetailCardTitle>
        {order.payments.events.map((event) => (
          <div className="order-detail-provider-event" key={event.id}>
            <i />
            <span>{event.name}</span>
            <code>{event.id}</code>
            <time>{event.time}</time>
          </div>
        ))}
      </OrderDetailCard>
    </div>
  );
}
