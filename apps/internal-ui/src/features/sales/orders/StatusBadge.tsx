import type { StatusBadge as StatusBadgeValue } from "./types";

export function StatusBadge({ value }: { value: StatusBadgeValue }) {
  return <span className="sales-orders-status" style={{ background: value.bg, color: value.color }}>{value.label}</span>;
}

export function MonoLink({ children }: { children: string }) {
  return <a className="sales-orders-mono-link" href="#" onClick={(event) => event.preventDefault()}>{children}</a>;
}
