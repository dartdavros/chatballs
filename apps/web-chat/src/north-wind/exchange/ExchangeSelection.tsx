import type { Size, StoreId } from "../model";
import { sizes } from "../products";
import { t } from "../language";
import type { ExchangeOptions, Order } from "./model";

export function ExchangeSelection({order, options, size, store, onSize, onStore, onReview, onChat}: {
  order: Order; options: ExchangeOptions | null; size: Size; store: StoreId;
  onSize: (size: Size) => void; onStore: (store: StoreId) => void; onReview: () => void; onChat: () => void;
}) {
  const available = options?.outcome === "available";
  const outOfStock = options?.outcome === "out_of_stock";
  return <div className="exchange-columns">
    <div className="exchange-panel">
      <h3>{t("exchange_product_order", {name: order.name, number: order.number})}</h3>
      <fieldset className="exchange-sizes">
        <legend>{t("exchange_new_size")}</legend>
        {sizes.filter(value => value !== order.size).map(value => <label key={value}>
          <input type="radio" name="exchange-size" checked={size === value} onChange={() => onSize(value)} /> {value}
        </label>)}
      </fieldset>
      <fieldset className="exchange-stores" aria-busy={!options}>
        <legend>{t("exchange_store")}</legend>
        {options?.pickupPoints.map(point => <label key={point.store}>
          <input type="radio" name="exchange-store" checked={store === point.store && point.available > 0}
            disabled={!available || !point.available} onChange={() => onStore(point.store)} />
          <span>{point.name}<br /><small>{point.available ? point.address : t("exchange_store_empty", {size})}</small></span>
        </label>)}
      </fieldset>
    </div>
    <div className="exchange-panel">
      <h3>{t("exchange_policy")}</h3>
      {options && <p>{t("exchange_policy_text", {days: options.exchangeDays})}</p>}
      {options && !available && <div className="exchange-status exchange-action is-warning">
        <strong>{outOfStock ? t("exchange_no_stock", {size}) : t("exchange_ineligible")}</strong>
        <p>{outOfStock ? t("exchange_no_stock_hint")
          : t(options.reason === "expired" ? "exchange_expired_hint" : "exchange_ineligible_hint")}</p>
        <button type="button" className="exchange-action" onClick={onChat}>{t("exchange_chat")}</button>
      </div>}
      {(!options || available) && <button className="exchange-action" type="button"
        disabled={!options?.pickupPoints.some(point => point.store === store && point.available > 0)} onClick={onReview}>
        {t("exchange_review")}
      </button>}
    </div>
  </div>;
}
