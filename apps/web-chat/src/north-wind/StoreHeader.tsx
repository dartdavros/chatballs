import { t } from "./language";
import { Icon } from "./Icons";
import type { ShopDisplay } from "./model";

type Props = {
  customer: ShopDisplay["customer"];
  personalized: boolean;
  favorites: number;
  compared: number;
  cart: boolean;
  showingFavorites: boolean;
  query: string;
  onBrowse: (mode?: "catalog" | "favorites") => void;
  onSearch: (query: string) => void;
  onCompare: () => void;
  onCart: () => void;
};

export function StoreHeader({customer, personalized, favorites, compared, cart, showingFavorites,
  query, onBrowse, onSearch, onCompare, onCart}: Props) {
  return <div className="store-header-shell">
    <div className="store-topline">
      <span><Icon name="MapPin" size={14} />{t("city")}</span>
      <span>{t("tagline")}</span>
    </div>
    <header className="shop-header">
      <button type="button" className="shop-brand" onClick={() => onBrowse()} aria-label={t("brand_catalog")}>
        <svg viewBox="0 0 39 31" width="31" height="25" aria-hidden="true">
          <path d="M2 28 16 3l7 13 5-8 9 20H2Z" fill="none" stroke="currentColor" strokeWidth="2.7" strokeLinejoin="round" />
          <path d="m11 12 5 4 5-4" fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
        <span>{t("brand")}</span>
      </button>
      <button type="button" className="store-catalog-button" onClick={() => onBrowse()}>
        <Icon name="Menu" size={19} />{t("catalog")}
      </button>
      <form className="store-search" role="search" onSubmit={event => { event.preventDefault(); onSearch(query); }}>
        <input aria-label={t("search_label")} placeholder={t("search_placeholder")} value={query}
          onChange={event => onSearch(event.target.value)} />
        {query && <button type="button" className="store-search-clear" onClick={() => onSearch("")} aria-label={t("clear_search")}>
          <Icon name="X" size={16} />
        </button>}
        <button type="submit" aria-label={t("find")}><Icon name="Search" size={19} /></button>
      </form>
      <nav className="store-header-actions" aria-label={t("account_nav")}>
        <details className="store-account">
          <summary><Icon name="User" size={21} /><span>{customer.name}</span></summary>
          <div className="store-account-menu">
            <strong>{customer.name}</strong><span>{customer.phone}</span><small>{t("signed_in")}</small>
            {personalized && <p>{t("card_discount")}</p>}
          </div>
        </details>
        <button type="button" className={showingFavorites ? "is-active" : ""} onClick={() => onBrowse("favorites")}
          aria-label={t("favorites_count", {count: favorites})}>
          <Icon name="Heart" size={21} /><span>{t("favorites")}</span>{favorites > 0 && <b>{favorites}</b>}
        </button>
        <button type="button" onClick={onCompare} aria-label={t("comparison_count", {count: compared})}>
          <Icon name="Compare" size={21} /><span>{t("comparison")}</span>{compared > 0 && <b>{compared}</b>}
        </button>
        <button type="button" onClick={onCart} aria-label={t("cart")}>
          <Icon name="ShoppingCart" size={21} /><span>{t("cart")}</span>{cart && <b>1</b>}
        </button>
      </nav>
    </header>
  </div>;
}
