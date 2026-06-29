import { Button } from "../../../shared/ui-controls";
import { OrderSuccessBadge } from "./OrderDetailBadge";
import { OrderDetailCard } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderSubscriptionTab({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-process">
      <div className="order-detail-section-head">
        <div>
          <h3>Подписка</h3>
          <span>{order.subscription.id}</span>
        </div>
        <OrderSuccessBadge>Активна</OrderSuccessBadge>
      </div>
      <div className="order-detail-fields three">
        <div><span>Текущий период</span><strong>{order.subscription.period}</strong></div>
        <div><span>Следующее списание</span><strong>{order.subscription.next}</strong></div>
        <div><span>Доступ</span><strong>{order.subscription.entitlement}</strong></div>
      </div>
      <div className="order-detail-section-actions">
        <Button variant="action" icon="refresh" iconSize={14}>Сверка</Button>
        <Button variant="action" icon="external" iconSize={14}>Открыть в продукте</Button>
      </div>
    </OrderDetailCard>
  );
}
