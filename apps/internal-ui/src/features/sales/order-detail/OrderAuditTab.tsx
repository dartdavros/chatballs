import { OrderDetailCard } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderAuditTab({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-table-card">
      <table className="order-detail-table">
        <thead>
          <tr><th>ВРЕМЯ</th><th>ДЕЙСТВИЕ</th><th>АКТОР</th><th>РЕЗУЛЬТАТ</th></tr>
        </thead>
        <tbody>
          {order.audit.map((event) => (
            <tr key={`${event.time}-${event.action}`}>
              <td className="nowrap">{event.time}</td>
              <td>{event.action}</td>
              <td><span className={`actor-${event.actorTone}`}>{event.actor}</span></td>
              <td><span className="success-text">{event.result}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </OrderDetailCard>
  );
}
