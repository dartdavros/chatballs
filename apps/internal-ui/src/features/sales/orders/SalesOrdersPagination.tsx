import { TablePagination } from "../../../shared/ui-controls";

export function SalesOrdersPagination({ shown, total }: { shown: number; total: number }) {
  return <TablePagination className="sales-orders-pagination" shown={shown} total={total} pages={[1, 2]} pageSizeLabel="20 / стр." />;
}
