import type { RouteKey } from "../../../types";
import { OrderSuccessBadge } from "./OrderDetailBadge";
import { OrderDetailActions } from "./OrderDetailActions";
import type { OrderDetail } from "./model";

export function OrderDetailHeader({ order, setRoute }: { order: OrderDetail; setRoute: (route: RouteKey) => void }) {
  const stats = [
    { label: "Сумма", value: order.amount, suffix: order.amountPeriod },
    { label: "Клиент", value: order.client, route: order.clientRoute },
    { label: "Продукт / тариф", value: order.offer },
    { label: "Дата", value: order.date },
    { label: "Источник", value: order.source.label, dot: order.source.color },
    { label: "Оформление", value: order.seller, dot: order.sellerColor, tone: "ai" },
  ];

  return (
    <section className="order-detail-header">
      <div className="order-detail-header-main">
        <div className="order-detail-title-row">
          <h1>{order.id}</h1>
          <OrderSuccessBadge>{order.status}</OrderSuccessBadge>
        </div>
        <div className="order-detail-meta">
          {stats.map((item) => (
            <div className="order-detail-meta-item" key={item.label}>
              <span>{item.label}</span>
              {item.route ? (
                <button type="button" onClick={() => setRoute(item.route)}>{item.value}</button>
              ) : (
                <strong className={item.tone === "ai" ? "ai" : ""}>
                  {item.dot && <i style={{ background: item.dot }} />}
                  {item.value}
                  {item.suffix && <em>{item.suffix}</em>}
                </strong>
              )}
            </div>
          ))}
        </div>
      </div>
      <OrderDetailActions />
    </section>
  );
}
