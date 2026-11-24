import type { Product } from "../model";
import { t } from "../language";
import type { VerifiedOrder } from "./model";

export function ExchangeOrder({verified, product, onExchange, onDefect}: {
  verified: VerifiedOrder; product: Product | undefined; onExchange: () => void; onDefect: () => void;
}) {
  const {order, shipment} = verified;
  const collected = shipment.status === "collected";
  return <div className="exchange-columns">
    <div className="exchange-panel">
      <h3>{t("exchange_your_order")}</h3>
      <div className="exchange-order">
        {product && <img src={product.photo} alt={order.name} />}
        <div><strong>{order.name}</strong><p>{t("exchange_item_size", {size: order.size})}</p></div>
      </div>
      <div className={`exchange-status${collected ? " is-success" : ""}`}>
        <strong>{t(`exchange_${shipment.status}`)}</strong>
        {collected && <p>{t("exchange_collected_hint")}</p>}
        {shipment.pickup && <p>{shipment.pickup.address} · {t("daily_hours", {close: shipment.pickup.closesAt})}</p>}
        {shipment.eta && <p>{t("exchange_eta", {date: shipment.eta})}</p>}
      </div>
      {collected && <button className="exchange-action" type="button" onClick={onExchange}>{t("exchange_begin")}</button>}
    </div>
    {collected && <div className="exchange-panel">
      <h3>{t("exchange_defect")}</h3>
      <button type="button" onClick={onDefect}>{t("exchange_send_photo")}</button>
    </div>}
  </div>;
}
