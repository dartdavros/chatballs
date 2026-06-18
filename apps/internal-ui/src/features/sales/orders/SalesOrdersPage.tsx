import { useMemo, useState } from "react";

import { salesOrdersData, salesOrderTabs } from "./model";
import { SalesOrdersHeader } from "./SalesOrdersHeader";
import { SalesOrdersPagination } from "./SalesOrdersPagination";
import { SalesOrdersTableCard } from "./SalesOrdersTableCard";
import { SalesOrdersTabs } from "./SalesOrdersTabs";
import type { SalesOrdersTab } from "./types";

export function SalesOrdersPage() {
  const [tab, setTab] = useState<SalesOrdersTab>("orders");
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const value = query.trim().toLowerCase();
    return salesOrdersData[tab].filter((row) => !value || row.search.includes(value));
  }, [query, tab]);
  const total = salesOrderTabs.find((item) => item.key === tab)?.count ?? rows.length;

  function selectTab(nextTab: SalesOrdersTab) {
    setTab(nextTab);
    setQuery("");
  }

  return (
    <>
      <SalesOrdersHeader query={query} setQuery={setQuery} />
      <SalesOrdersTabs activeTab={tab} setActiveTab={selectTab} />
      <SalesOrdersTableCard activeTab={tab} rows={rows} />
      <SalesOrdersPagination shown={rows.length} total={total} />
    </>
  );
}
