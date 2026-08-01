import type { ReactNode } from "react";

import { Icon } from "../icons";

/** Русское склонение существительного по количеству: 1 знание, 2 знания, 5 знаний. */
export function pluralize(count: number, forms: [string, string, string]): string {
  const remainder100 = count % 100;
  const remainder10 = count % 10;
  if (remainder100 >= 11 && remainder100 <= 14) return forms[2];
  if (remainder10 === 1) return forms[0];
  if (remainder10 >= 2 && remainder10 <= 4) return forms[1];
  return forms[2];
}

/** Панель массовых действий над выбранными материалами библиотеки. */
export function BulkSelectionBar({
  children,
  count,
  forms,
  onClear,
}: {
  children: ReactNode;
  count: number;
  forms: [string, string, string];
  onClear: () => void;
}) {
  return (
    <div className="knowledge-bulk-bar">
      <span className="knowledge-bulk-check"><Icon name="check" size={12} /></span>
      <strong>Выбрано {count} {pluralize(count, forms)}</strong>
      <i />
      {children}
      <span />
      <button className="knowledge-bulk-clear" type="button" onClick={onClear}>Снять выбор</button>
    </div>
  );
}
