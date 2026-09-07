import type { ReactNode } from "react";

import { Icon } from "../../shared/icons";

/** Подвал таблиц порталов: подпись слева, страницы справа (кадры PT1/PT3).
 *  Один вид на оба списка раздела — у списка порталов и у библиотеки статей
 *  подвал в макете одинаковый; стрелки на границах гасятся (кадр PT1). */
export function PortalTableFooter({
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
    <div className="portal-table-footer">
      <span>{note}</span>
      <span className="portal-pages">
        <button
          aria-label="Предыдущая страница"
          className="portal-page-step"
          disabled={page <= 1}
          type="button"
          onClick={() => onPageChange(page - 1)}
        >
          <Icon name="chevron" size={14} strokeWidth={2} />
        </button>
        {pages.map((item) => (item === page
          ? <b key={item}>{item}</b>
          : <button className="portal-page-number" key={item} type="button" onClick={() => onPageChange(item)}>{item}</button>))}
        <button
          aria-label="Следующая страница"
          className="portal-page-step"
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
