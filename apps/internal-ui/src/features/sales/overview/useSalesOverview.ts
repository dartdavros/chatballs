import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { SalesStats } from "./model";
import type { SalesPeriod } from "./types";

export function useSalesOverview(period: SalesPeriod) {
  const [stats, setStats] = useState<SalesStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    api<SalesStats>(`/api/v1/conversations/stats/?period=${period}`)
      .then((data) => {
        if (active) setStats(data);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [period]);

  return { stats, loading, error };
}
