import { fmt, t } from "./language";
import { useEffect, useState } from 'react';
import type { ShopDisplay, StoreId } from './model';
import { money, storeLabel } from './products';
import { Icon } from './Icons';

type Props = {
  state: ShopDisplay;
  store: StoreId;
  bonus: number;
  pending: boolean;
  error: string;
  onBack: () => void;
  onCheckout: () => void;
  onStore: (store: StoreId) => void;
  onBonusChange: (enabled: boolean, amount: number) => void;
};

export function CartDetails({ state, store, bonus, pending, error, onBack, onCheckout, onStore, onBonusChange }: Props) {
  const cart = state.cart;
  const order = state.order;
  const quote = order ?? state.quote;
  const limit = Math.max(0, quote?.maxBonus ?? 0);
  const suggestedAmount = Math.min(Math.max(1, bonus || 750), limit);
  const bonusSelected = !order && bonus > 0;
  const allowed = limit > 0;
  const [amountDraft, setAmountDraft] = useState(String(suggestedAmount));
  useEffect(() => setAmountDraft(String(suggestedAmount)), [suggestedAmount]);
  const bonusApplied = order?.bonusSpent ?? quote?.bonusSpent ?? 0;
  const price = quote?.personalPrice ?? cart?.personalPrice ?? 0;
  const total = quote?.total ?? price;
  const selectedStore = order?.store ?? store;
  const selectedInventory = state.inventory.find(row => row.store === selectedStore);
  const address = order?.address ?? selectedInventory?.address ?? '';
  const balance = order ? order.balanceAfter : quote?.bonusBalance ?? state.customer.balance;

  function changeAmount(raw: string) {
    setAmountDraft(raw);
    if (!raw.trim()) return;
    const value = Number(raw);
    if (Number.isFinite(value) && value >= 1) onBonusChange?.(true, Math.min(limit, Math.floor(value)));
  }
  function finishAmount() {
    const value = Math.min(limit, Math.max(1, Math.floor(Number(amountDraft)) || suggestedAmount));
    setAmountDraft(String(value));
    onBonusChange?.(true, value);
  }

  return <section className="demo-checkout demo-checkout--inline" aria-labelledby="ski-checkout-title">
    <header className="demo-checkout-heading">
      <button type="button" className="demo-checkout-back cursor-interaction" onClick={onBack}><Icon name="ArrowLeft" size={16} />{order ? t("keep_shopping") : t("back_products")}</button>

      <div><h1 id="ski-checkout-title">{order ? t("order_placed") : t("checkout")}</h1>{cart && !order && <span>{t("one_product")}</span>}</div>
    </header>

    {!cart || !quote ? <div className="demo-checkout-empty">
      <span><Icon name="ShoppingBag" size={30} /></span><h2>{t("cart_empty")}</h2>
      <p>{t("cart_empty_hint")}</p>
      <button type="button" className="ski-primary-button cursor-interaction" onClick={onBack}>{t("browse_products")}<Icon name="ArrowRight" size={16} /></button>
    </div> : <div className="demo-checkout-grid">
      <div className="demo-checkout-main">
        {order && <div className="demo-checkout-success" role="status"><Icon name="CheckCircle2" size={22} /><div><strong>{t("order_confirmed", {number: order.number})}</strong><p>{t("reserved")}</p></div></div>}
        <section className="demo-checkout-section">
          <h2>{order ? t("your_order") : t("order_items")}</h2>
          <div className="demo-checkout-product">
            <img src={state.product.photo} alt={t("suit_photo_alt", {name: cart.productName})} />
            <div className="demo-checkout-product-info"><span>{t("suit_kind")}</span><h3>{cart.productName}</h3><p>{state.product.colorName}</p><div className="demo-checkout-product-meta"><span>{t("selected_size", {size: cart.size})}</span><span>{t("one_piece")}</span></div></div>
            <div className="demo-checkout-product-price"><strong>{money(price)}</strong>{state.product.price < state.product.basePrice && <><s>{money(state.product.basePrice)}</s><small>{t("discount_included")}</small></>}</div>
          </div>
        </section>

        <section className="demo-checkout-section">
          <h2>{t("collection")}</h2>
          <div className="demo-checkout-method"><span><Icon name="MapPin" size={18} />{t("store_pickup")}</span><strong>{t("free")}</strong></div>
          {order ? <div className="demo-checkout-selected-store"><strong>{t("store_quoted", {name: storeLabel(selectedStore)})}</strong><p>{address}</p><span>{selectedInventory?.hours}</span></div> :
            <div className="demo-checkout-stores" role="radiogroup" aria-label={t("pickup_store")}>
              {state.inventory.map(row => <label key={row.store} className={'demo-checkout-store' + (row.store === selectedStore ? ' is-selected' : '') + (row.available < 1 ? ' is-unavailable' : '')}>
                <input type="radio" name="pickup-store" value={row.store} checked={row.store === selectedStore} disabled={row.available < 1 || !onStore} onChange={() => onStore?.(row.store)} />
                <span><strong>{t("store_quoted", {name: storeLabel(row.store)})}</strong><span>{row.address}</span><small>{row.available > 0 ? row.hours : t("size_unavailable")}</small></span>
              </label>)}
            </div>}
        </section>

        <section className="demo-checkout-section">
          <h2>{t("recipient")}</h2>
          <div className="demo-checkout-recipient"><span className="demo-checkout-avatar">{state.customer.name.slice(0, 1)}</span><div><strong>{state.customer.name}</strong><span>{state.customer.phone}</span></div><span className="demo-checkout-account">{t("profile_data")}</span></div>
        </section>

        <section className="demo-checkout-section demo-checkout-payment">
          <h2>{t("payment")}</h2>
          <div className="demo-checkout-payment-method"><span className="demo-checkout-radio-mark" /><div><strong>{t("on_collection")}</strong><span>{t("payment_method")}</span></div></div>
          {order ? <div className="demo-checkout-bonus-result"><div><span>{t("points_used")}</span><strong>{fmt.number(order.bonusSpent)}</strong></div><div><span>{t("points_left")}</span><strong>{fmt.number(balance)}</strong></div></div> :
            <div className="demo-checkout-bonuses">
              <label className={'demo-checkout-bonus-toggle' + (!allowed ? ' is-unavailable' : '')}>
                <input type="checkbox" checked={!!bonusSelected} disabled={!allowed || !onBonusChange} onChange={event => onBonusChange?.(event.target.checked, suggestedAmount)} />
                <span><strong>{t("redeem_points", {count: fmt.number(suggestedAmount)})}</strong><small>{t("points_balance", {count: fmt.number(balance)})}</small></span>
                {bonusSelected && <b>−{money(bonusApplied)}</b>}
              </label>
              {bonusSelected && <div className="demo-checkout-bonus-amount">
                <label htmlFor="ski-bonus-amount">{t("points_input")}</label>
                <div><input id="ski-bonus-amount" type="number" min={1} max={limit} step={1} inputMode="numeric" value={amountDraft} onChange={event => changeAmount(event.target.value)} onBlur={finishAmount} aria-describedby="ski-bonus-limit" /><span>{t("points")}</span><button type="button" onClick={() => { setAmountDraft(String(limit)); onBonusChange?.(true, limit); }}>{t("all_available")}</button></div>
                <small id="ski-bonus-limit">{t("points_limit", {count: fmt.number(limit)})}</small>
              </div>}
              {!allowed && <p className="demo-checkout-bonus-note">{t("points_excluded")}</p>}

            </div>}
        </section>
      </div>

      <aside className="demo-checkout-summary" aria-label={t("order_summary")}>
        <h2>{order ? t("order_summary") : t("your_order")}</h2>{error && <p role="alert" className="demo-checkout-bonus-note">{error}</p>}
        <dl aria-live="polite" aria-atomic="true"><div><dt>{t("one_product")}</dt><dd>{money(price)}</dd></div><div><dt>{t("pickup")}</dt><dd>{t("free")}</dd></div>{bonusApplied > 0 && <div className="is-bonus"><dt>{order ? t("redeemed_points") : t("redeem_summary")}</dt><dd>−{money(bonusApplied)}</dd></div>}<div className="is-total"><dt>{order ? t("due_on_pickup") : t("total")}</dt><dd>{money(total)}</dd></div></dl>
        {!order && <button type="button" className="ski-primary-button demo-checkout-submit cursor-interaction" onClick={onCheckout} disabled={pending || !selectedInventory || selectedInventory.available < 1 || bonus !== quote.bonusSpent}>{t("place_order")}<Icon name="ArrowRight" size={16} /></button>}
        {order ? <div className="demo-checkout-summary-pickup"><Icon name="MapPin" size={17} /><div><strong>{t("pickup_store_name", {name: storeLabel(selectedStore)})}</strong><span>{address}</span></div></div> : <p className="demo-checkout-summary-note">{t("pickup_payment_hint")}</p>}
      </aside>
    </div>}
  </section>;
}
