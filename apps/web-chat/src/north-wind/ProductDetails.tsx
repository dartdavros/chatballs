import { t } from "./language";
import { useEffect, useRef, useState } from 'react';
import type { Product, ProductId } from './model';
import { money, storeLabel, stores, type Size } from './products';
import { Icon } from './Icons';
import { trapModalTab } from './modalFocus';

export function useModalKeys(onClose: () => void, enabled = true) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!enabled) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const keydown = (event: KeyboardEvent) => {
      if (ref.current?.closest('[inert]')) return;
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      trapModalTab(event, ref.current);
    };
    window.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = previous; window.removeEventListener('keydown', keydown); };
  }, [onClose, enabled]);
  return ref;
}

export function ProductDetails({ product, selectedSize, onSize, onBuy, onClose }: {
  product: Product; selectedSize: Size; onSize: (size: Size) => void; onBuy: (id: ProductId) => void; onClose: () => void;
}) {
  const [zoom, setZoom] = useState(false);
  const ref = useModalKeys(() => zoom ? setZoom(false) : onClose());
  useEffect(() => setZoom(false), [product.id]);
  const stock = product.stockBySize[selectedSize];
  return <div className="demo-product-backdrop" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={ref} className={`demo-product-details${zoom ? ' is-zoomed' : ''}`} id={`ski-product-${product.id}`} role="dialog" aria-modal="true" aria-labelledby={`ski-title-${product.id}`}>
      <header className="demo-product-details-nav"><button type="button" className="link has-icon cursor-interaction" onClick={() => zoom ? setZoom(false) : onClose()}><Icon name="ArrowLeft" size={15} />{zoom ? t("back_description") : t("back_store")}</button><button type="button" className="demo-product-close cursor-interaction" onClick={onClose} aria-label={t("close_product")} autoFocus><Icon name="X" size={19} /></button></header>
      <div className="demo-product-details-body">
        <button type="button" className="demo-product-details-photo cursor-interaction" onClick={() => setZoom(value => !value)} aria-label={zoom ? t("zoom_out") : t("zoom_in")}><img src={product.photo} alt={t("suit_photo_alt", {name: product.name})} />{!zoom && <span><Icon name="Search" size={13} />{t("zoom_in")}</span>}</button>
        {!zoom && <div className="demo-product-details-info">
          <p className="demo-product-type">{t("suit_kind")} · {product.article}</p><h2 id={`ski-title-${product.id}`}>{product.name}</h2>
          <div className="ski-personal-price"><strong>{money(product.price)}</strong>{product.price < product.basePrice && <><s>{money(product.basePrice)}</s><span>−10%</span></>}</div>{product.price < product.basePrice && <p className="ski-personal-hint">{t("personal_discount")}</p>}
          <p className="demo-product-reason">{product.description}</p>
          <h3>{t("size")}</h3>{<div className="ski-size-picker" role="group" aria-label={t("suit_size")}>{product.sizes.map(size => <button key={size} type="button" className={`cursor-interaction${selectedSize === size ? ' is-selected' : ''}`} aria-pressed={selectedSize === size} onClick={() => onSize(size)}>{size}</button>)}</div>}
          {<button type="button" className="ski-primary-button demo-product-choose cursor-interaction" onClick={() => onBuy(product.id)}>{t("buy")}<Icon name="ShoppingBag" size={17} /></button>}
          <h3>{t("for_slopes")}</h3><dl className="demo-product-facts"><div><dt>{t("material")}</dt><dd>{product.material}</dd></div><div><dt>{t("lining")}</dt><dd>{product.lining}</dd></div><div><dt>{t("membrane")}</dt><dd>{product.membrane}</dd></div><div><dt>{t("breathability")}</dt><dd>{product.breathability}</dd></div><div><dt>{t("colour")}</dt><dd>{product.colorName}</dd></div><div><dt>{t("set")}</dt><dd>{t("jacket_and_pants")}</dd></div></dl>
          <h3>{t("stores_in_kazan")}</h3><div className="demo-product-details-stores">{stores.map(store => <div key={store}><span><Icon name="MapPin" size={15} />{storeLabel(store)}</span><strong>{stock[store] ? t("stock_count", {count: stock[store]}) : t("out_of_stock")}</strong></div>)}</div>
        </div>}
      </div>
      {zoom && <span className="ski-sr-only" id={`ski-title-${product.id}`}>{t("large_suit_photo", {name: product.name})}</span>}
    </section>
  </div>;
}
