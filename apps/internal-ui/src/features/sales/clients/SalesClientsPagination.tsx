import { TablePagination } from "../../../shared/ui-controls";

export function SalesClientsPagination({ shownCount }: { shownCount: number }) {
  return <TablePagination className="sales-clients-pagination" shown={shownCount} total={248} pages={[1, 2, 3, "ellipsis", 25]} pageSizeLabel="10 / стр." />;
}
