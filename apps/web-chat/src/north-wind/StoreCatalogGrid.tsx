import { t } from "./language";
import { Icon } from "./Icons";
import type { Product, ProductId } from "./model";
import { money } from "./products";

type Props = {
  products: Product[];
  favorites: ProductId[];
  compared: ProductId[];
  onProduct: (id: ProductId) => void;
  onBuy: (id: ProductId) => void;
  onFavorite: (id: ProductId) => void;
  onCompare: (id: ProductId) => void;
};

export function StoreCatalogGrid({products, favorites, compared, onProduct, onBuy, onFavorite, onCompare}: Props) {
  return <div className="store-product-grid">
    {products.map(item => {
      const favorite = favorites.includes(item.id);
      const compare = compared.includes(item.id);
      const discount = item.price < item.basePrice;
      const title = t("men_suit_title", {name: item.name});
      return <article className="store-catalog-card" key={item.id}>
        <div className="store-catalog-image">
          <button type="button" className="store-catalog-photo" onClick={() => onProduct(item.id)} aria-label={t("open_product", {name: item.name})}>
            <img src={item.photo} alt={title} loading="lazy" />
          </button>
          {discount && <span className="store-sale-tag">−10%</span>}
          <button type="button" className={`store-card-favorite${favorite ? " is-active" : ""}`} onClick={() => onFavorite(item.id)}
            aria-label={favorite ? t("favorite_remove", {name: item.name}) : t("favorite_add", {name: item.name})} aria-pressed={favorite}>
            <Icon name="Heart" size={19} />
          </button>
        </div>
        <div className="store-card-price">
          <strong>{money(item.price)}</strong>{discount && <s>{money(item.basePrice)}</s>}
        </div>
        <button type="button" className="store-card-title" onClick={() => onProduct(item.id)}>
          {t("men_suit")} <strong>{item.name}</strong>
        </button>
        <p>{item.colorName} · {item.sizes.join(", ")}</p>
        <div className="store-card-actions">
          <button type="button" className="store-buy-button" onClick={() => onBuy(item.id)}>{t("buy")}</button>
          <button type="button" className={`store-compare-button${compare ? " is-active" : ""}`}
            aria-label={compare ? t("compare_remove", {name: item.name}) : t("compare_product", {name: item.name})} aria-pressed={compare}
            onClick={() => onCompare(item.id)}><Icon name="Compare" size={19} /></button>
        </div>
      </article>;
    })}
  </div>;
}
