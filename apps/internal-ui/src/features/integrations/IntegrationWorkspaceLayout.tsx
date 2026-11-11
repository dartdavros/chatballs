import type { ReactNode } from "react";

export function IntegrationWorkspaceLayout({ children }: { children: ReactNode }) {
  return <div className="settings-layout">
    <section className="settings-content is-single">
      <div className="settings-content-inner">{children}</div>
    </section>
  </div>;
}
