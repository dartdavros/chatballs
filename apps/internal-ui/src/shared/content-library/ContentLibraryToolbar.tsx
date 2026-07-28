import type { ReactNode } from "react";

import { SearchInput } from "../ui-controls";

export function ContentLibraryToolbar({
  action,
  children,
  onQueryChange,
  placeholder = "Поиск по заголовку и описанию",
  query,
}: {
  action?: ReactNode;
  children?: ReactNode;
  onQueryChange: (query: string) => void;
  placeholder?: string;
  query: string;
}) {
  return (
    <div className="knowledge-toolbar">
      <SearchInput placeholder={placeholder} value={query} onChange={onQueryChange} />
      {children}
      {action}
    </div>
  );
}
