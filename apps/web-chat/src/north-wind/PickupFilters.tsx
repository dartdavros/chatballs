import type { Size, StoreId } from "./model";
import { t } from "./language";
import { Icon } from "./Icons";
import { sizes, storeLabel, stores } from "./products";
import "./pickup-filters.css";

export const defaultPickupBudget = 35_000;
const maximumPickupBudget = 1_000_000;

export function PickupFilters({size, store, budget, onSize, onStore, onBudget, onSelection}: {
  size: Size;
  store: StoreId;
  budget: number;
  onSize: (size: Size) => void;
  onStore: (store: StoreId) => void;
  onBudget: (budget: number) => void;
  onSelection: () => void;
}) {
  return <form className="store-pickup-filters" onSubmit={event => { event.preventDefault(); onSelection(); }}>
    <span className="store-pickup-filter"><Icon name="MapPin" size={15} />{t("city")}</span>
    <label className="store-pickup-filter is-selected">{t("size")}
      <select value={size} onChange={event => onSize(event.target.value as Size)}>
        {sizes.map(value => <option key={value} value={value}>{value}</option>)}
      </select>
    </label>
    <label className="store-pickup-filter">{t("store_pickup")}
      <select value={store} onChange={event => onStore(event.target.value as StoreId)}>
        {stores.map(value => <option key={value} value={value}>{storeLabel(value)}</option>)}
      </select>
    </label>
    <label className="store-pickup-filter">{t("pickup_budget")}
      <input type="number" min={0} max={maximumPickupBudget} inputMode="numeric" required value={budget}
        onChange={event => onBudget(event.target.valueAsNumber || 0)} />
    </label>
    <button className="store-secondary-button" type="submit">{t("pickup_select")}</button>
  </form>;
}
