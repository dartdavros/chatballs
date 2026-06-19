import { Icon } from "../../../shared/icons";
import { OrderDetailCard, OrderDetailCardTitle } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderTimeline({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-timeline-card">
      <OrderDetailCardTitle>Ход заказа</OrderDetailCardTitle>
      <div className="order-detail-timeline">
        {order.timeline.map((item, index) => (
          <div className="order-detail-timeline-node-wrap" key={item.label}>
            <div className={`order-detail-timeline-node ${item.done ? "done" : "pending"}`}>
              <div>{item.done ? <Icon name="check" size={16} /> : <span />}</div>
              <strong>{item.label}</strong>
              <em className={item.active ? "active" : ""}>{item.time}</em>
            </div>
            {index < order.timeline.length - 1 && <span className={`order-detail-timeline-line ${item.done ? "done" : ""}`} />}
          </div>
        ))}
      </div>
    </OrderDetailCard>
  );
}
