import { useMemo, useState } from "react";

import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { ActionButton, Button, SearchInput, TablePagination } from "../../../shared/ui-controls";
import type { Product, RouteKey } from "../../../types";
import { AddSaleDialog } from "./AddSaleDialog";
import { toSaleRow } from "./model";
import { SalesRegistryFilters } from "./SalesRegistryFilters";
import { SalesRegistryTable } from "./SalesRegistryTable";
import { emptyFilters, useSales, type SalesFilters } from "./useSales";

export function SalesRegistryPage({
  products,
  openSale,
  openDialog,
}: {
  products: Product[];
  setRoute: (route: RouteKey) => void;
  openSale: (id: number) => void;
  openDialog: (conversationId: number) => void;
}) {
  const [filters, setFilters] = useState<SalesFilters>(emptyFilters);
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const { sales, loading, error, reload } = useSales(filters);

  const rows = useMemo(() => {
    const value = query.trim().toLowerCase();
    return sales.map(toSaleRow).filter((row) => !value || row.search.includes(value));
  }, [sales, query]);

  return (
    <>
      <div className="sales-orders-header">
        <div>
          <h1>Продажи</h1>
          <p>Единый реестр состоявшихся продаж · сумма, возврат, чистая выручка, источник и атрибуция</p>
        </div>
        <div className="sales-orders-header-actions">
          <SearchInput className="sales-orders-search" value={query} onChange={setQuery} placeholder="Поиск по продаже или клиенту…" />
          <ActionButton icon="download">Экспорт</ActionButton>
          <Button variant="primary" icon="plus" onClick={() => setAdding(true)}>Добавить продажу</Button>
        </div>
      </div>

      <SalesRegistryFilters filters={filters} setFilters={setFilters} />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <EmptyState title="Не удалось загрузить продажи" />
      ) : (
        <>
          <div className="sales-orders-card">
            <div className="sales-orders-table-scroll">
              <SalesRegistryTable rows={rows} openSale={openSale} openDialog={openDialog} />
              {rows.length === 0 && (
                <div className="sales-orders-empty">
                  <div><Icon name="search" size={22} /></div>
                  <strong>Продажи не найдены</strong>
                  <span>Измените фильтры или добавьте продажу вручную.</span>
                </div>
              )}
            </div>
          </div>
          <TablePagination className="sales-orders-pagination" shown={rows.length} total={sales.length} pages={[1]} pageSizeLabel="20 / стр." />
        </>
      )}

      <AddSaleDialog products={products} open={adding} onClose={() => setAdding(false)} onSaved={reload} />
    </>
  );
}
