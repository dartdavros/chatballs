import { Icon } from "../../../shared/icons";
import { paginationItems } from "../../../shared/ui-controls";

// Страницы в подвале карточки списка (кадр K1).
export function SalesClientsPagination({ page, pageCount, setPage }: { page: number; pageCount: number; setPage: (page: number) => void }) {
  return (
    <div className="sales-clients-pager">
      <button type="button" aria-label="Предыдущая страница" disabled={page === 1} onClick={() => setPage(page - 1)}>
        <Icon name="chevron" size={13} strokeWidth={2.2} />
      </button>
      {paginationItems(page, pageCount).map((item, index) => (
        item === "ellipsis"
          ? <span key={`gap-${index}`}>…</span>
          : <button className={item === page ? "is-active" : ""} type="button" key={item} onClick={() => setPage(item)}>{item}</button>
      ))}
      <button className="is-next" type="button" aria-label="Следующая страница" disabled={page === pageCount} onClick={() => setPage(page + 1)}>
        <Icon name="chevron" size={13} strokeWidth={2.2} />
      </button>
    </div>
  );
}
