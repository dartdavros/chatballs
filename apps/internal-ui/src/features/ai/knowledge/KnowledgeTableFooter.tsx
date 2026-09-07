import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";

/** Подвал таблицы знаний: подпись слева, страницы справа (кадр KB1).
 *  Стрелки на границах гасятся — как в подвале библиотеки портала. */
export function KnowledgeTableFooter({
  note,
  page,
  pageCount,
  onPageChange,
}: {
  note: ReactNode;
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  const pages = Array.from({ length: pageCount }, (_, index) => index + 1);
  return (
    <div className="knowledge-table-footer">
      <span>{note}</span>
      <span className="knowledge-pages">
        <button
          aria-label="Предыдущая страница"
          className="knowledge-page-step"
          disabled={page <= 1}
          type="button"
          onClick={() => onPageChange(page - 1)}
        >
          <Icon name="chevron" size={14} strokeWidth={2} />
        </button>
        {pages.map((item) => (item === page
          ? <b key={item}>{item}</b>
          : <button className="knowledge-page-number" key={item} type="button" onClick={() => onPageChange(item)}>{item}</button>))}
        <button
          aria-label="Следующая страница"
          className="knowledge-page-step"
          disabled={page >= pageCount}
          type="button"
          onClick={() => onPageChange(page + 1)}
        >
          <Icon name="chevron" size={14} strokeWidth={2} />
        </button>
      </span>
    </div>
  );
}
