import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { ApiSale } from "./model";

export type SalesFilters = {
  status: string;
  sourceType: string;
  attribution: string;
};

export const emptyFilters: SalesFilters = { status: "", sourceType: "", attribution: "" };

function toQuery(filters: SalesFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.sourceType) params.set("sourceType", filters.sourceType);
  if (filters.attribution) params.set("attribution", filters.attribution);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function useSales(filters: SalesFilters) {
  const [sales, setSales] = useState<ApiSale[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await api<{ items: ApiSale[] }>(`/api/v1/sales/${toQuery(filters)}`);
      setSales(data.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  return { sales, loading, error, reload: load };
}
