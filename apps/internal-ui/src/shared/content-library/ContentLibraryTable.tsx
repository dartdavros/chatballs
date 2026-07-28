import type { ReactNode } from "react";

import { Icon } from "../icons";
import { LoadingState } from "../ui";
import { Button } from "../ui-controls";

export function ContentLibraryTable({
  canCreate = false,
  children,
  createLabel,
  emptyDescription,
  emptyTitle,
  error,
  errorTitle,
  footer,
  hasItems,
  loading,
  onCreate,
  onRetry,
}: {
  canCreate?: boolean;
  children: ReactNode;
  createLabel?: string;
  emptyDescription?: string;
  emptyTitle: string;
  error: boolean;
  errorTitle: string;
  footer?: ReactNode;
  hasItems: boolean;
  loading: boolean;
  onCreate?: () => void;
  onRetry: () => void;
}) {
  if (loading) {
    return <div className="knowledge-table-state"><LoadingState variant="inline" /></div>;
  }
  if (error) {
    return (
      <div className="knowledge-table-state">
        <strong>{errorTitle}</strong>
        <Button variant="secondary" onClick={onRetry}>Повторить</Button>
      </div>
    );
  }
  if (!hasItems) {
    return (
      <div className={emptyDescription ? "knowledge-empty-category" : "knowledge-table-state"}>
        {emptyDescription && <span><Icon name="folder" size={24} /></span>}
        <strong>{emptyTitle}</strong>
        {emptyDescription && <p>{emptyDescription}</p>}
        {canCreate && onCreate && createLabel && (
          <Button variant="primary" onClick={onCreate}>{createLabel}</Button>
        )}
      </div>
    );
  }
  return (
    <div className="table-card knowledge-table-card">
      {children}
      {footer}
    </div>
  );
}
