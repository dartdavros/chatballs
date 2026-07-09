import { useEffect, useState } from "react";

import { api } from "../../api/client";

// Реальные операционные метрики отдела продаж (SPEC §12 требует операционные
// метрики без выдуманных чисел). Backend: conversations/stats возвращает
// ops.openDialogs + period.sales + period.revenueMinor. Заглушки/мок не используем.
type SalesStats = {
  ops: { openDialogs: number };
  period: { sales: number; revenueMinor: number };
};

export type SalesDepartmentStats = {
  openDialogs: number;
  sales: number;
  revenueMinor: number;
};

export function useDepartmentStats() {
  const [stats, setStats] = useState<SalesDepartmentStats | null>(null);

  useEffect(() => {
    let active = true;
    api<SalesStats>("/api/v1/conversations/stats/?period=today")
      .then((data) => {
        if (!active) return;
        setStats({
          openDialogs: data.ops?.openDialogs ?? 0,
          sales: data.period?.sales ?? 0,
          revenueMinor: data.period?.revenueMinor ?? 0,
        });
      })
      .catch(() => {
        // Транзиентная ошибка — карточка покажет «—» (как и для support).
      });
    return () => {
      active = false;
    };
  }, []);

  return stats;
}

export function formatRubMinor(minor: number): string {
  // revenueMinor — копейки (согласовано с sales overview model.ts: minor / 100).
  return `₽${Math.round(minor / 100).toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`;
}
