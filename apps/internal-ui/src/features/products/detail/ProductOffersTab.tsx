import { formatPrice } from "../model";
import type { Product } from "../../../types";
import { offerType } from "./model";

export function ProductOffersTab({ product }: { product: Product }) {
  const prices = product.offers.flatMap((offer) => offer.prices.map((price) => ({ offer, price })));
  return (
    <div className="product-offers-tab">
      <p className="product-offers-note">Активные Offer привязаны к версии цены. Изменение цены создаёт новую версию — прошлые заказы не затрагиваются.</p>
      <div className="product-offer-grid">
        {product.offers.length ? product.offers.map((offer) => (
          <section className="product-offer-card" key={offer.id}>
            <div><h3>{offer.name}</h3><span>{offerType(offer)}</span></div>
            <strong>{offer.prices.filter((price) => price.isActive).map(formatPrice).join(" · ") || "—"}</strong>
            <p>{offer.description || "—"}</p>
            <footer><code>{offer.code}</code>{offer.aiOfferable && <span>AI может предлагать</span>}</footer>
          </section>
        )) : <section className="product-detail-card product-wide-empty">—</section>}
      </div>
      <section className="product-price-history">
        <h3>История версий цен</h3>
        <table><thead><tr><th>ВЕРСИЯ</th><th>OFFER</th><th>ЦЕНА</th><th>ДЕЙСТВУЕТ С</th><th>СТАТУС</th></tr></thead>
          <tbody>{prices.map(({ offer, price }) => <tr key={price.id}><td>v{price.version}</td><td>{offer.name}</td><td>{formatPrice(price)}</td><td>{new Intl.DateTimeFormat("ru-RU").format(new Date(price.validFrom))}</td><td><span className={price.isActive ? "active" : "archive"}>{price.isActive ? "Активна" : "Архив"}</span></td></tr>)}</tbody>
        </table>
        {!prices.length && <div className="product-price-empty">—</div>}
      </section>
    </div>
  );
}
