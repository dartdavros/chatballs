import { Icon } from "../../../shared/icons";

export function paginationItems(page: number, pageCount: number): Array<number | "ellipsis"> {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, index) => index + 1);
  const pages = new Set([1, pageCount, page - 1, page, page + 1]);
  const visible = [...pages].filter((item) => item >= 1 && item <= pageCount).sort((a, b) => a - b);
  const result: Array<number | "ellipsis"> = [];
  visible.forEach((item, index) => {
    if (index > 0 && item - visible[index - 1] > 1) result.push("ellipsis");
    result.push(item);
  });
  return result;
}

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
