import { useMemo, useState } from "react";

import { EmptyState, LoadingState } from "../../shared/ui";
import { SalesChart } from "./overview/SalesChart";
import { SalesKpiSection } from "./overview/SalesKpiSection";
import { SalesOverviewGrid } from "./overview/SalesOverviewGrid";
import { SalesOverviewHeader } from "./overview/SalesOverviewHeader";
import { buildSalesOverviewVm } from "./overview/model";
import type { SalesPeriod } from "./overview/types";
import { useSalesOverview } from "./overview/useSalesOverview";

export function SalesOverviewPage({ openConversation }: { openConversation: (conversationId: number) => void }) {
  const [period, setPeriod] = useState<SalesPeriod>("today");
  const { stats, loading, error } = useSalesOverview(period);
  const vm = useMemo(() => (stats ? buildSalesOverviewVm(period, stats) : null), [period, stats]);

  return (
    <>
      <SalesOverviewHeader period={period} setPeriod={setPeriod} />
      {loading && !vm ? (
        <LoadingState />
      ) : error || !vm ? (
        <EmptyState title="Не удалось загрузить обзор" />
      ) : (
        <>
          <SalesKpiSection label="ОПЕРАЦИОННЫЕ · СЕЙЧАС" items={vm.opsKpi} />
          <SalesKpiSection label={`РЕЗУЛЬТАТ · ${vm.periodLabel.toUpperCase()}`} items={vm.resKpi} result />
          <SalesChart vm={vm} />
          <SalesOverviewGrid vm={vm} openConversation={openConversation} />
        </>
      )}
    </>
  );
}
