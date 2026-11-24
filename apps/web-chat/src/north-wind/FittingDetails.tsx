import { fmt, t } from "./language";
import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "./Icons";
import type { Product, ProductId, StoreId } from "./model";
import { storeLabel, stores } from "./products";
import { ShopRequestError, storefrontApi } from "./shopApi";

type Booking = {number: number; startsAt: string; address: string; minutes: number};
const dayFormat = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Europe/Moscow", year: "numeric", month: "2-digit", day: "2-digit",
});


export function FittingDetails({token, products, onBack}: {
  token: string; products: Product[]; onBack: () => void;
}) {
  const api = useMemo(() => storefrontApi(token), [token]);
  const today = dayFormat.format(new Date());
  const timeFormat = new Intl.DateTimeFormat(fmt.tag(), {
    timeZone: "Europe/Moscow", hour: "2-digit", minute: "2-digit",
  });
  const bookingDate = new Intl.DateTimeFormat(fmt.tag(), {timeZone: "Europe/Moscow", dateStyle: "medium"});
  const [day, setDay] = useState(today);
  const [store, setStore] = useState<StoreId>("gorki");
  const [first, setFirst] = useState<ProductId>("alpine");
  const [second, setSecond] = useState<ProductId>("ridge");
  const [slots, setSlots] = useState<string[]>([]);
  const [selected, setSelected] = useState("");
  const [booking, setBooking] = useState<Booking | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [revision, reload] = useState(0);
  const attempt = useRef<{signature: string; id: string} | null>(null);
  const running = useRef(false);

  useEffect(() => {
    let current = true;
    setLoaded(false);
    setSelected("");
    api<string[]>("fitting-slots", {store, day}).then(result => {
      if (current) {
        setSlots(result);
        setLoaded(true);
      }
    }).catch(() => {
      if (current) {
        setSlots([]);
        setLoaded(true);
        setError(t("fitting_slots_error"));
      }
    });
    return () => { current = false; };
  }, [api, day, store, first, second, revision]);

  async function confirm() {
    if (running.current || !selected || first === second) return;
    const values = {store, starts_at: selected, products: [first, second], confirmed: true};
    const signature = JSON.stringify(values);
    const requestId = attempt.current?.signature === signature ? attempt.current.id : crypto.randomUUID();
    attempt.current = {signature, id: requestId};
    running.current = true;
    setError("");
    setBusy(true);
    try {
      setBooking(await api<Booking>("fitting", values, requestId));
    } catch (failure) {
      const occupied = failure instanceof ShopRequestError && failure.code === "fitting_slot_unavailable";
      setError(occupied ? t("fitting_occupied") : t("fitting_confirm_error"));
      if (occupied) reload(previous => previous + 1);
    } finally {
      running.current = false;
      setBusy(false);
    }
  }

  return <section className="demo-checkout demo-checkout--inline" aria-labelledby="fitting-title">
    <header className="demo-checkout-heading">
      <button type="button" className="demo-checkout-back" onClick={onBack}>
        <Icon name="ArrowLeft" size={16} />{t("back_products")}
      </button>
      <div><h1 id="fitting-title">{t("fitting_title")}</h1></div>
    </header>
    {booking ? <div className="demo-checkout-success" role="status">
      <Icon name="CheckCircle2" size={22} />
      <div>
        <strong>{t("booking_confirmed", {number: booking.number})}</strong>
        <p>{bookingDate.format(new Date(booking.startsAt))} · {timeFormat.format(new Date(booking.startsAt))} · {booking.address}</p>
      </div>
    </div> : <div className="demo-checkout-grid">
      <div className="demo-checkout-main">
        <section className="demo-checkout-section">
          <h2>{t("suits")}</h2>
          <div className="demo-checkout-stores">
            <label>{t("first_model")} <select value={first} onChange={event => setFirst(event.target.value as ProductId)}>
              {products.map(product => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select></label>
            <label>{t("second_model")} <select value={second} onChange={event => setSecond(event.target.value as ProductId)}>
              {products.map(product => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select></label>
          </div>
        </section>
        <section className="demo-checkout-section">
          <h2>{t("where_when")}</h2>
          <div className="demo-checkout-stores">
            <label>{t("store")} <select value={store} onChange={event => { setError(""); setStore(event.target.value as StoreId); }}>
              {stores.map(id => <option key={id} value={id}>{storeLabel(id)}</option>)}
            </select></label>
            <label>{t("date")} <input type="date" value={day} min={today}
              onChange={event => { if (event.target.value) { setError(""); setDay(event.target.value); } }} /></label>
          </div>
          {loaded && slots.length ? <div>
            <label htmlFor="north-wind-fitting-time">{t("time")}</label>{" "}
            <select id="north-wind-fitting-time" value={selected} onChange={event => setSelected(event.target.value)}>
              <option value="">{t("choose_time")}</option>
              {slots.map(slot => <option key={slot} value={slot}>{timeFormat.format(new Date(slot))}</option>)}
            </select>
          </div> : <p role="status">{loaded ? t("no_slots") : t("checking_schedule")}</p>}
        </section>
      </div>
      <aside className="demo-checkout-summary">
        <h2>{t("visit")}</h2>
        <dl><div><dt>{t("duration")}</dt><dd>{t("fitting_duration")}</dd></div><div><dt>{t("fitting")}</dt><dd>{t("free")}</dd></div></dl>
        {error && <p className="demo-checkout-bonus-note" role="alert">{error}</p>}
        <button type="button" className="ski-primary-button demo-checkout-submit" onClick={() => void confirm()}
          disabled={!loaded || !selected || first === second || busy}>{t("confirm_fitting")}<Icon name="ArrowRight" size={16} /></button>
      </aside>
    </div>}
  </section>;
}
