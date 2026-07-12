import type { SalesFilters } from "./useSales";

const STATUS_OPTIONS: Array<[string, string]> = [
  ["", "Все состояния"],
  ["CONFIRMED", "Подтверждена"],
  ["PARTIALLY_REFUNDED", "Частичный возврат"],
  ["REFUNDED", "Возврат"],
  ["CANCELLED", "Отменена"],
];

const SOURCE_OPTIONS: Array<[string, string]> = [
  ["", "Все источники"],
  ["PRODUCT_API", "Product API"],
  ["MANUAL", "Ручная"],
  ["LEGACY_IMPORT", "Legacy import"],
];

const ATTRIBUTION_OPTIONS: Array<[string, string]> = [
  ["", "Атрибуция: любая"],
  ["with", "С атрибуцией"],
  ["without", "Без атрибуции"],
];

function FilterSelect({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: Array<[string, string]> }) {
  return (
    <label className="sales-registry-filter">
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([key, label]) => (
          <option value={key} key={key}>{label}</option>
        ))}
      </select>
    </label>
  );
}

export function SalesRegistryFilters({ filters, setFilters }: { filters: SalesFilters; setFilters: (filters: SalesFilters) => void }) {
  return (
    <div className="sales-registry-filters">
      <FilterSelect value={filters.status} onChange={(status) => setFilters({ ...filters, status })} options={STATUS_OPTIONS} />
      <FilterSelect value={filters.sourceType} onChange={(sourceType) => setFilters({ ...filters, sourceType })} options={SOURCE_OPTIONS} />
      <FilterSelect value={filters.attribution} onChange={(attribution) => setFilters({ ...filters, attribution })} options={ATTRIBUTION_OPTIONS} />
    </div>
  );
}
