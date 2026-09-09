import type { ReactNode } from "react";

import { Icon } from "./icons";
import { paginationItems } from "./ui-controls";
import "./pagination.css";
import { t } from "../i18n";

// Единственный подвал со страницами в приложении: списки порталов, статей,
// контактов, сотрудников, агентов и журнал аудита. Страницу считает сервер —
// компонент только рисует номера и сообщает о выборе.

export function Pagination({
  page,
  pageCount,
  onPage,
  note,
  className = "",
}: {
  page: number;
  pageCount: number;
  onPage: (page: number) => void;
  /** Подпись слева: «Показано 20 из 45», подсказка про архив и т.п. */
  note?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`pager ${className}`.trim()}>
      <span className="pager-note">{note}</span>
      <span className="pager-pages">
        <button
          aria-label={t("shared.previous_page")}
          className="pager-step"
          disabled={page <= 1}
          type="button"
          onClick={() => onPage(page - 1)}
        >
          <Icon name="chevronLeft" size={14} strokeWidth={2} />
        </button>
        {paginationItems(page, pageCount).map((item, index) => (
          item === "ellipsis"
            ? <span key={`gap-${index}`}>…</span>
            : (
              <button
                aria-current={item === page ? "page" : undefined}
                className={`pager-number ${item === page ? "is-current" : ""}`.trim()}
                disabled={item === page}
                key={item}
                type="button"
                onClick={() => onPage(item)}
              >
                {item}
              </button>
            )
        ))}
        <button
          aria-label={t("shared.next_page")}
          className="pager-step"
          disabled={page >= pageCount}
          type="button"
          onClick={() => onPage(page + 1)}
        >
          <Icon name="chevronRight" size={14} strokeWidth={2} />
        </button>
      </span>
    </div>
  );
}
