import type { RouteKey } from "../../../types";
import { OrderSuccessBadge } from "./OrderDetailBadge";
import { OrderDetailCard, OrderDetailCardTitle } from "./OrderDetailCard";
import type { OrderDetail } from "./model";

export function OrderSummaryTab({ order, setRoute }: { order: OrderDetail; setRoute: (route: RouteKey) => void }) {
  return (
    <div className="order-detail-summary-grid">
      <div className="order-detail-summary-main">
        <OrderItemsCard order={order} />
        <AcceptedDocumentsCard order={order} />
      </div>
      <aside className="order-detail-summary-side">
        <BuyerCard order={order} />
        <SourceCard order={order} setRoute={setRoute} />
      </aside>
    </div>
  );
}

function OrderItemsCard({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-table-card">
      <OrderDetailCardTitle subtitle="Снимок на момент оформления · цена зафиксирована">Позиции заказа</OrderDetailCardTitle>
      <table className="order-detail-table">
        <thead>
          <tr><th>ТАРИФ</th><th>ТИП</th><th className="numeric">ЦЕНА</th><th className="numeric">КОЛ-ВО</th><th className="numeric">ИТОГО</th></tr>
        </thead>
        <tbody>
          {order.items.map((item) => (
            <tr key={item.code}>
              <td><strong>{item.offer}</strong><span>{item.code}</span></td>
              <td>{item.type}</td>
              <td className="numeric">{item.price}</td>
              <td className="numeric">{item.qty}</td>
              <td className="numeric"><b>{item.total}</b></td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr><td colSpan={4}>Итого к оплате</td><td className="numeric">{order.amount}</td></tr></tfoot>
      </table>
    </OrderDetailCard>
  );
}

function AcceptedDocumentsCard({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-documents">
      <OrderDetailCardTitle>Принятые документы</OrderDetailCardTitle>
      {order.documents.map((document) => (
        <div className="order-detail-document-row" key={document.title}>
          <OrderSuccessBadge className="icon-only"> </OrderSuccessBadge>
          <span>{document.title} {document.version && <em>{document.version}</em>}</span>
          <time>{document.accepted}</time>
        </div>
      ))}
    </OrderDetailCard>
  );
}

function BuyerCard({ order }: { order: OrderDetail }) {
  return (
    <OrderDetailCard className="order-detail-side-card">
      <OrderDetailCardTitle>Данные покупателя</OrderDetailCardTitle>
      <strong>{order.buyer.name}</strong>
      <code>{order.buyer.email}</code>
      <span>{order.buyer.company}</span>
    </OrderDetailCard>
  );
}

function SourceCard({ order, setRoute }: { order: OrderDetail; setRoute: (route: RouteKey) => void }) {
  return (
    <OrderDetailCard className="order-detail-side-card">
      <OrderDetailCardTitle>Источник оформления</OrderDetailCardTitle>
      <p><i style={{ background: order.source.color }} />{order.checkout.title}</p>
      <button className="order-detail-checkout-link" type="button" onClick={() => setRoute("salesDialogs")}>{order.checkout.id}</button>
      <span>{order.checkout.created}</span>
    </OrderDetailCard>
  );
}
