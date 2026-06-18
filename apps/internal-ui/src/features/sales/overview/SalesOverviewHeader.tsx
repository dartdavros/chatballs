import { Segmented } from "../../../shared/ui";
import type { SalesPeriod } from "./types";

export function SalesOverviewHeader({ period, setPeriod }: { period: SalesPeriod; setPeriod: (period: SalesPeriod) => void }) {
  return (
    <div className="sales-overview-header">
      <div>
        <h1>Обзор отдела продаж</h1>
        <p>Операционное состояние и результаты · обновлено только что</p>
      </div>
      <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
    </div>
  );
}
