import type { ReactNode } from "react";

export function ContentEditorCard({
  actions,
  children,
  error,
  heading,
  meta,
}: {
  actions?: ReactNode;
  children: ReactNode;
  error?: string | null;
  heading: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <section className="knowledge-editor-card knowledge-main-card">
      <div className="knowledge-card-heading">
        {heading}
        {meta}
      </div>
      {children}
      {error && <div className="knowledge-editor-error">{error}</div>}
      {actions && <div className="knowledge-editor-actions">{actions}</div>}
    </section>
  );
}
