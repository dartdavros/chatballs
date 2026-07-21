import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";

export function RailCard({ title, icon, iconColor, count, action, side, children }: { title: string; icon: "plug" | "warning"; iconColor: string; count?: string; action?: string; side?: ReactNode; children: ReactNode }) {
  return (
    <section className="rail-card">
      <div className="rail-card-head">
        <div><span className="rail-icon" style={{ color: iconColor }}><Icon name={icon} size={17} /></span><strong>{title}</strong>{count && <b>{count}</b>}</div>
        {action && <button className="link" type="button">{action}</button>}
        {side}
      </div>
      <div className="rail-card-body">{children}</div>
    </section>
  );
}
