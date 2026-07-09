import type { ReactNode } from "react";

// Строительный блок секции правой панели (используется sales ClientContext,
// ProductContext, HistoryContext и support OperatorCards). Класс sales-* — design
// baseline, переиспользуется без переименования (SPEC §8.4 layout без изменений).
export function ContextSection({ title, action, children }: { title: string; action?: string; children: ReactNode }) {
  return (
    <section className="sales-context-section">
      <div className="sales-context-section-head">
        <h4>{title}</h4>
        {action && <button>{action}</button>}
      </div>
      {children}
    </section>
  );
}
