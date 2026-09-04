import type { MetricItem } from "./types";

export function MetricGroup({ title, columns, items }: { title: string; columns: 4 | 5; items: MetricItem[] }) {
  return (
    <>
      <div className="metric-group-title">{title}</div>
      <div className="metric-group-grid" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {items.map((item) => (
          <div className="metric-cell" key={item.label}>
            <div>{item.dot && <span style={{ background: item.dot }} />}{item.label}</div>
            <strong style={{ color: item.color ?? "var(--text-body)" }}>{item.value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}
