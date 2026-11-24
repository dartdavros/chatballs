import { createI18n } from "@chatballs/shared";
import { Icon } from "./Icons";
import type { ProductId, Size } from "./model";
import { en } from "./messages.en";
import { ru, type ShopMessageKey } from "./messages.ru";
import "./pickup-recommendations.css";

type Recommendation = {
  id: ProductId;
  name: string;
  basePrice: number;
  insulation: number;
  membrane: number;
  url?: string;
  stock?: string;
  availability?: string;
  available?: boolean;
};

export type PickupRecommendationSet = {
  language: string;
  size?: Size;
  heading: string;
  followup: string;
  products: Recommendation[];
};

function productUrl(path: string) {
  const url = new URL(path, window.location.origin);
  return url.origin === window.location.origin && url.pathname === "/chat/north-wind.html" ? url.href : undefined;
}

export function PickupRecommendations({selection}: {selection: PickupRecommendationSet}) {
  const i18n = createI18n<ShopMessageKey>({catalogs: {ru, en}, source: "ru"});
  i18n.setLanguage(selection.language === "en" ? "en" : "ru");
  const {fmt, t} = i18n;
  return <div className="cb-pickup-selection">
    <p>{selection.heading}</p>
    {selection.products.map(product => {
      const href = product.url ? productUrl(product.url) : undefined;
      return <article key={product.id} className="cb-pickup-card">
        {href ? <a className="cb-pickup-photo" href={href} target="_blank" rel="noopener noreferrer">
          <ProductPhoto product={product} alt={t("suit_photo_alt", {name: product.name})} />
        </a> : <div className="cb-pickup-photo"><ProductPhoto product={product} alt={t("suit_photo_alt", {name: product.name})} /></div>}
        <div className="cb-pickup-content">
          <div className="cb-pickup-type">{t("men_suit")}{selection.size && <> · {t("size")} {selection.size}</>}</div>
          <header className="cb-pickup-heading"><h3>{product.name}</h3><strong>{t("price", {amount: fmt.number(product.basePrice)})}</strong></header>
          <p className="cb-pickup-reason">{t(`description_${product.id}`)}</p>
          <dl className="cb-pickup-facts">
            <div><dt>{t("material")}</dt><dd>{t(`material_${product.id}`)}</dd></div>
            <div><dt>{t("lining")}</dt><dd>{t("insulation_measure", {amount: fmt.number(product.insulation)})}</dd></div>
            <div><dt>{t("membrane")}</dt><dd>{t("membrane_measure", {amount: fmt.number(product.membrane)})}</dd></div>
          </dl>
          {product.stock && <p className="cb-pickup-reason">{product.stock}</p>}
          {product.available === false ? <p className="cb-pickup-reason">{product.availability}</p> :
            <div className="cb-pickup-stock"><Icon name="Check" size={14} />{t("pickup_available")}</div>}
          {href && <div className="cb-pickup-footer"><a href={href} target="_blank" rel="noopener noreferrer">{t("open_product", {name: product.name})}<Icon name="ArrowRight" size={16} /></a></div>}
        </div>
      </article>;
    })}
    <p>{selection.followup}</p>
  </div>;
}

function ProductPhoto({product, alt}: {product: Recommendation; alt: string}) {
  return <img src={`${import.meta.env.BASE_URL}north-wind/images/${product.id}.png`} alt={alt} />;
}
