import type { ReactNode } from "react";

export function ContextSection({ title, action, children }: { title: string; action?: string; children: ReactNode }) {
  return <section className="sales-context-section"><div className="sales-context-section-head"><h4>{title}</h4>{action && <button>{action}</button>}</div>{children}</section>;
}
