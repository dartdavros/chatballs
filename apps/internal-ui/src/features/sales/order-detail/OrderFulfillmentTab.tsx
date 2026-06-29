import { Button } from "../../../shared/ui-controls";
import { OrderSuccessBadge } from "./OrderDetailBadge";
import { OrderDetailCard } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderFulfillmentTab({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-process">
      <div className="order-detail-section-head">
        <div>
          <h3>Доступ продукта</h3>
          <span>{order.fulfillment.id}</span>
        </div>
        <div className="order-detail-section-actions">
          <OrderSuccessBadge>Активен</OrderSuccessBadge>
          <Button variant="action" icon="refresh" iconSize={14}>Сверка</Button>
        </div>
      </div>
      <div className="order-detail-fields three">
        <div><span>Попытки</span><strong>{order.fulfillment.attempts}</strong></div>
        <div><span>Результат</span><strong className="success-text">{order.fulfillment.result}</strong></div>
        <div><span>Обновлено</span><strong>{order.fulfillment.updated}</strong></div>
      </div>
      <div className="order-detail-payload-label">ДАННЫЕ ОПЕРАЦИИ</div>
      <pre>{order.fulfillment.payload}</pre>
    </OrderDetailCard>
  );
}
