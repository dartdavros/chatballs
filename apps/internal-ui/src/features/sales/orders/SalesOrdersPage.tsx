import { useMemo, useState } from "react";

import { EmptyState, LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { toFulfillmentRow, toOrderRow, toPaymentRow } from "./model";
import { SalesOrdersHeader } from "./SalesOrdersHeader";
import { SalesOrdersPagination } from "./SalesOrdersPagination";
import { SalesOrdersTableCard } from "./SalesOrdersTableCard";
import { SalesOrdersTabs } from "./SalesOrdersTabs";
import type { SalesOrdersTab } from "./types";
import { useOrders } from "./useOrders";

export function SalesOrdersPage({ setRoute, openOrder }: { setRoute: (route: RouteKey) => void; openOrder: (id: number) => void }) {
  const { orders, loading, error } = useOrders();
  const [tab, setTab] = useState<SalesOrdersTab>("orders");
  const [query, setQuery] = useState("");

  const byTab = useMemo(
    () => ({
      orders: orders.map(toOrderRow),
      subs: [] as Array<{ search: string }>,
      pays: orders.map(toPaymentRow),
      refunds: [] as Array<{ search: string }>,
      exec: orders.map(toFulfillmentRow),
    }),
    [orders],
  );

  const counts: Record<SalesOrdersTab, number> = { orders: byTab.orders.length, subs: 0, pays: byTab.pays.length, refunds: 0, exec: byTab.exec.length };

  const rows = useMemo(() => {
    const value = query.trim().toLowerCase();
    return byTab[tab].filter((row) => !value || row.search.includes(value));
  }, [byTab, query, tab]);

  function selectTab(nextTab: SalesOrdersTab) {
    setTab(nextTab);
    setQuery("");
  }

  return (
    <>
      <SalesOrdersHeader query={query} setQuery={setQuery} />
      <SalesOrdersTabs activeTab={tab} setActiveTab={selectTab} counts={counts} />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <EmptyState title="Не удалось загрузить заказы" />
      ) : tab === "subs" || tab === "refunds" ? (
        <EmptyState title={tab === "subs" ? "Подписки появятся с расширением домена" : "Возвраты появятся с расширением домена"} />
      ) : (
        <>
          <SalesOrdersTableCard activeTab={tab} rows={rows} openOrder={openOrder} />
          <SalesOrdersPagination shown={rows.length} total={counts[tab]} />
        </>
      )}
    </>
  );
}
