import { Icon } from "../../../shared/icons";
import type { KpiItem } from "./types";

export function SalesKpiSection({ items, label, result = false }: { items: KpiItem[]; label: string; result?: boolean }) {
  return (
    <>
      <div className="sales-section-title">{label}</div>
      <div className="sales-kpi-grid">
        {items.map((item) => <SalesKpiCard item={item} result={result} key={item.label} />)}
      </div>
    </>
  );
}

function SalesKpiCard({ item, result = false }: { item: KpiItem; result?: boolean }) {
  return (
    <article className="sales-kpi-card">
      <span>{item.dot && <i style={{ background: item.dot }} />}{item.label}</span>
      <strong style={{ color: item.valueColor }}>{item.value}</strong>
      {result && item.deltaText ? (
        <small className="sales-kpi-delta" style={{ color: item.deltaColor }}>
          <span className={item.down ? "is-down" : ""}><Icon name="chevron" size={13} /></span>
          {item.deltaText}<em>{item.sub}</em>
        </small>
      ) : <small style={{ color: item.subColor }}>{item.sub}</small>}
    </article>
  );
}
