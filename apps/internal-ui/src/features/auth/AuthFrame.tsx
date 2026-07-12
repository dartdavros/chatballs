import type { ReactNode } from "react";

import { LogoIcon, ShieldIcon } from "../../shared/icons";

export function AuthFrame({ title, subtitle, logo, width = 400, children, note }: { title: string; subtitle: ReactNode; logo: "pulse" | "shield"; width?: number; children: ReactNode; note?: ReactNode }) {
  return (
    <main className="auth-screen">
      <div className="auth-box" style={{ width }}>
        <div className="auth-brand">
          <div className="auth-logo">{logo === "shield" ? <ShieldIcon /> : <LogoIcon />}</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {children}
        {note && <div className="auth-note">{note}</div>}
      </div>
    </main>
  );
}
