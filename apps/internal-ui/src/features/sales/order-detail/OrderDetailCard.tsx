import type { ReactNode } from "react";

export function OrderDetailCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`order-detail-card ${className}`.trim()}>{children}</section>;
}

export function OrderDetailCardTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div className="order-detail-card-title">
      <h3>{children}</h3>
      {subtitle && <span>{subtitle}</span>}
    </div>
  );
}
