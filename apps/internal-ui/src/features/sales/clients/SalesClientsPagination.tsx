import { TablePagination } from "../../../shared/ui-controls";

export function SalesClientsPagination({ shownCount, totalCount }: { shownCount: number; totalCount: number }) {
  return <TablePagination className="sales-clients-pagination" shown={shownCount} total={totalCount} pages={[1]} pageSizeLabel={`${Math.max(shownCount, 1)} / стр.`} />;
}
