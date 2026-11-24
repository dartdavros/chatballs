import type { Product, Size, StoreId } from "../model";
import { storeLabel } from "../products";
import { t } from "../language";
import { ExchangeOrder } from "./ExchangeOrder";
import { ExchangeSelection } from "./ExchangeSelection";
import type { Order } from "./model";
import { useExchange } from "./useExchange";
import "./exchange.css";

export function ExchangeFlow({token, orderNumber, products, widgetKey, prepared}: {
  token: string; orderNumber: number; products: Product[]; widgetKey: string; prepared: boolean;
}) {
  const flow = useExchange(token, orderNumber, widgetKey, prepared);
  const {phase, verified, result, error} = flow;
  const orderTitle = t("exchange_order", {number: orderNumber});
  const title = {
    order: orderTitle, select: flow.options && flow.options.outcome !== "available" ? t("exchange_alternatives") : t("exchange_select"),
    confirm: t("exchange_confirm"), done: t("exchange_result"), defect: t("exchange_defect"),
  }[phase];
  const order = verified?.order;
  return <section className="exchange-frame" aria-labelledby="north-wind-exchange-title">
    <div className="exchange-content">
      <h2 id="north-wind-exchange-title">{title}</h2>
      {!verified && (error === "order_unavailable" ? <div className="exchange-columns">
        <div className="exchange-panel">
          <h3>{t("exchange_access")}</h3>
          <div className="exchange-status is-warning" role="alert">
            <strong>{t("exchange_access_denied")}</strong><p>{t("exchange_access_hint")}</p>
          </div>
        </div>
      </div> : !error && <p role="status">{t("shop_loading")}</p>)}
      {verified && phase === "order" && <ExchangeOrder verified={verified}
        product={products.find(value => value.id === verified.order.productId)}
        onExchange={() => flow.changePhase("select")} onDefect={() => flow.changePhase("defect")} />}
      {order && phase === "select" && <ExchangeSelection order={order} options={flow.options} size={flow.size} store={flow.store}
        onSize={flow.setSize} onStore={flow.setStore} onReview={() => flow.changePhase("confirm")} onChat={flow.startChat} />}
      {order && phase === "confirm" && <ExchangeConfirmation
        order={order} size={flow.size} store={flow.store} pending={flow.pending} onConfirm={flow.confirm} />}
      {order && phase === "done" && result && <>
        <div className="exchange-status is-success" role="status">
          <strong>{t("exchange_result_created", {number: result.number})}</strong><p>{t("exchange_result_status")}</p>
        </div>
        <p className="exchange-action">{order.name} · {order.size} → {result.targetSize} · {storeLabel(result.store)} · {result.address}</p>
      </>}
      {phase === "defect" && <>
        <div className="exchange-status">
          <strong>{t("exchange_send_photo")}</strong><p>{t("exchange_send_photo_hint")}</p>
        </div>
        <button type="button" className="exchange-action" onClick={flow.startChat}>{t("exchange_chat")}</button>
      </>}
      {error && error !== "order_unavailable" && <p className="exchange-status exchange-action is-warning" role="alert">
        {t(error === "stock_unavailable" ? "error_stock_unavailable" : "error_shop_unavailable")}
      </p>}
    </div>
  </section>;
}

function ExchangeConfirmation({order, size, store, pending, onConfirm}: {
  order: Order; size: Size; store: StoreId; pending: boolean; onConfirm: () => void;
}) {
  return <div className="exchange-columns" aria-busy={pending}>
    <div className="exchange-panel">
      <h3>{t("exchange_confirm_review")}</h3>
      <dl>
        <dt>{t("exchange_order_label")}</dt><dd>№ {order.number}</dd>
        <dt>{t("exchange_model_label")}</dt><dd>{order.name}</dd>
        <dt>{t("size")}</dt><dd>{order.size} → {size}</dd>
        <dt>{t("exchange_store_label")}</dt><dd>{storeLabel(store)}</dd>
      </dl>
      <button type="button" disabled={pending} onClick={onConfirm}>{t("exchange_confirm_button")}</button>
    </div>
    <div className="exchange-panel exchange-progress" data-pending={pending}>
      {pending && <>
        <h3>{t("exchange_progress")}</h3>
        <div className="exchange-status" role="status">
          <strong>{t("exchange_stock_check")}</strong><p>{t("exchange_stock_check_hint")}</p>
        </div>
        <button type="button" className="exchange-action" disabled>{t("exchange_pending")}</button>
      </>}
    </div>
  </div>;
}
