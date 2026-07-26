import { TablePagination } from "../../../shared/ui-controls";

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

export function SalesClientsPagination({ page, pageCount, shownCount, totalCount, setPage }: { page: number; pageCount: number; shownCount: number; totalCount: number; setPage: (page: number) => void }) {
  return <TablePagination className="sales-clients-pagination" currentPage={page} onPageChange={setPage} shown={shownCount} total={totalCount} pages={paginationItems(page, pageCount)} pageSizeLabel="20 / стр." />;
}
