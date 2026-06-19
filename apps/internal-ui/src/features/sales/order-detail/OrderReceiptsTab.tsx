import { OrderSuccessBadge } from "./OrderDetailBadge";
import { OrderDetailCard } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderReceiptsTab({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-receipt">
      <div className="order-detail-section-head">
        <h3>Фискальный чек</h3>
        <OrderSuccessBadge>Отправлен в ОФД</OrderSuccessBadge>
      </div>
      <div className="order-detail-fields">
        {order.receipt.map((item) => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong className={item.mono ? "mono" : ""}>{item.value}</strong>
          </div>
        ))}
      </div>
    </OrderDetailCard>
  );
}
