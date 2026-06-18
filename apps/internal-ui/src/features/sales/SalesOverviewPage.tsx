import { useMemo, useState } from "react";

import type { Product } from "../../types";
import { SalesChart } from "./overview/SalesChart";
import { SalesKpiSection } from "./overview/SalesKpiSection";
import { SalesOverviewGrid } from "./overview/SalesOverviewGrid";
import { SalesOverviewHeader } from "./overview/SalesOverviewHeader";
import { salesOverviewModel } from "./overview/model";
import type { SalesPeriod } from "./overview/types";

export function SalesOverviewPage({ products }: { products: Product[] }) {
  const [period, setPeriod] = useState<SalesPeriod>("today");
  const vm = useMemo(() => salesOverviewModel(period, products), [period, products]);

  return (
    <>
      <SalesOverviewHeader period={period} setPeriod={setPeriod} />
      <SalesKpiSection label="ОПЕРАЦИОННЫЕ · СЕЙЧАС" items={vm.opsKpi} />
      <SalesKpiSection label={`РЕЗУЛЬТАТ · ${vm.periodLabel.toUpperCase()}`} items={vm.resKpi} result />
      <SalesChart vm={vm} />
      <SalesOverviewGrid vm={vm} />
    </>
  );
}
