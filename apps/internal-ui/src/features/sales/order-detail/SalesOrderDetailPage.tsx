import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import { StatusBadge } from "../orders/StatusBadge";
import { fulfillmentBadge, paymentBadge, rub } from "../orders/model";
import { useOrderDetail } from "./useOrderDetail";

const FULFILLMENT_ACTIONS: Array<{ value: string; label: string }> = [
  { value: "PENDING", label: "В процессе" },
  { value: "DELIVERED", label: "Исполнен" },
  { value: "FAILED", label: "Ошибка" },
];

function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

export function SalesOrderDetailPage({ orderId, setRoute }: { orderId: number | null; setRoute: (route: RouteKey) => void }) {
  const { order, loading, error, busy, markPaid, cancel, setFulfillment } = useOrderDetail(orderId);

  if (loading) return <LoadingState />;
  if (error || !order) return <EmptyState title="Не удалось загрузить заказ" />;

  const cancelled = order.paymentStatus === "CANCELLED";

  return (
    <div className="order-detail-page">
      <button className="order-detail-back" type="button" onClick={() => setRoute("salesOrders")}><Icon name="arrow" size={15} />К заказам</button>

      <section className="ai-card order-detail-head">
        <div className="order-detail-title">
          <h1>{order.code}</h1>
          <StatusBadge value={paymentBadge(order.paymentStatus)} />
          <StatusBadge value={fulfillmentBadge(order.fulfillmentStatus)} />
        </div>
        <div className="order-detail-meta">
          <div><span>Клиент</span><b>{order.contact.name}</b></div>
          <div><span>Продукт</span><b>{order.product ? order.product.name : "—"}</b></div>
          <div><span>Канал</span><b>{order.channel || "—"}</b></div>
          <div><span>Создан</span><b>{formatDateTime(order.createdAt)}</b></div>
          <div><span>Оплачен</span><b>{order.paidAt ? formatDateTime(order.paidAt) : "—"}</b></div>
          <div><span>Сумма</span><b className="order-detail-amount">{rub(order.amountMinor)}</b></div>
        </div>
      </section>

      <section className="ai-card ai-card--flush">
        <div className="order-detail-section-head"><h3>Позиции</h3></div>
        <table className="sales-client-detail-table">
          <thead><tr><th>OFFER</th><th>НАЗВАНИЕ</th><th className="numeric">КОЛ-ВО</th><th className="numeric">СУММА</th></tr></thead>
          <tbody>
            {(order.items ?? []).map((item) => (
              <tr key={item.id}>
                <td><code>{item.offerCode}</code></td>
                <td>{item.title}</td>
                <td className="numeric">{item.quantity}</td>
                <td className="numeric"><strong>{rub(item.amountMinor)}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="ai-card order-detail-actions">
        <h3>Действия</h3>
        <div className="order-detail-action-row">
          {order.paymentStatus === "PENDING" && <Button variant="primary" icon="check" disabled={busy} onClick={markPaid}>Отметить оплаченным</Button>}
          {!cancelled && order.paymentStatus !== "PAID" && <Button variant="danger-outline" disabled={busy} onClick={cancel}>Отменить заказ</Button>}
        </div>
        <div className="order-detail-fulfillment">
          <span>Исполнение:</span>
          {FULFILLMENT_ACTIONS.map((action) => (
            <Button key={action.value} variant="secondary" disabled={busy || order.fulfillmentStatus === action.value} onClick={() => setFulfillment(action.value)}>{action.label}</Button>
          ))}
        </div>
      </section>
    </div>
  );
}
