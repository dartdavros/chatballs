import { useState } from "react";

import { Button } from "../../../shared/ui-controls";
import { formatPrice } from "../model";
import type { Product, ProductOffer } from "../../../types";
import { offerType } from "./model";
import { OfferFormModal } from "./OfferFormModal";
import { PriceFormModal } from "./PriceFormModal";

export function ProductOffersTab({ product, reload }: { product: Product; reload: () => void }) {
  const prices = product.offers.flatMap((offer) => offer.prices.map((price) => ({ offer, price })));
  const [offerModal, setOfferModal] = useState<{ open: boolean; offer?: ProductOffer }>({ open: false });
  const [priceModal, setPriceModal] = useState<{ open: boolean; offerId: number | null; offerName: string }>({ open: false, offerId: null, offerName: "" });

  return (
    <div className="product-offers-tab">
      <div className="product-offers-head">
        <p className="product-offers-note">Активные предложения привязаны к версии цены. Изменение цены создаёт новую версию — прошлые версии не редактируются.</p>
        <Button variant="primary" icon="plus" onClick={() => setOfferModal({ open: true })}>Добавить предложение</Button>
      </div>
      <div className="product-offer-grid">
        {product.offers.length ? product.offers.map((offer) => (
          <section className={`product-offer-card${offer.isActive ? "" : " is-inactive"}`} key={offer.id}>
            <div><h3>{offer.name}</h3><span>{offerType(offer)}</span></div>
            <strong>{offer.prices.filter((price) => price.isActive).map(formatPrice).join(" · ") || "—"}</strong>
            <p>{offer.description || "—"}</p>
            <footer><code>{offer.code}</code>{offer.aiOfferable && <span>AI может предлагать</span>}{!offer.isActive && <span className="offer-inactive">Неактивно</span>}</footer>
            <div className="offer-card-actions">
              <Button variant="secondary" icon="edit" onClick={() => setOfferModal({ open: true, offer })}>Изменить</Button>
              <Button variant="secondary" icon="percent" onClick={() => setPriceModal({ open: true, offerId: offer.id, offerName: offer.name })}>Новая цена</Button>
            </div>
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

      <OfferFormModal productId={product.id} offers={product.offers} offer={offerModal.offer} open={offerModal.open} onClose={() => setOfferModal({ open: false })} onSaved={reload} />
      <PriceFormModal productId={product.id} offerId={priceModal.offerId} offerName={priceModal.offerName} open={priceModal.open} onClose={() => setPriceModal({ open: false, offerId: null, offerName: "" })} onSaved={reload} />
    </div>
  );
}
