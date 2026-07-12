import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { ApiSale } from "../registry/model";

export function useSaleDetail(saleId: number | null) {
  const [sale, setSale] = useState<ApiSale | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  const load = useCallback(async () => {
    if (saleId === null) {
      setError(true);
      setLoading(false);
      return;
    }
    try {
      const { sale: data } = await api<{ sale: ApiSale }>(`/api/v1/sales/${saleId}/`);
      setSale(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [saleId]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = useCallback(
    async (action: string, body?: object) => {
      if (saleId === null) return;
      setBusy(true);
      setActionError("");
      try {
        await api(`/api/v1/sales/${saleId}/${action}/`, { method: "POST", body: body ? JSON.stringify(body) : undefined });
        await load();
      } catch (requestError) {
        setActionError(requestError instanceof Error ? requestError.message : "Не удалось выполнить действие");
      } finally {
        setBusy(false);
      }
    },
    [saleId, load],
  );

  return {
    sale,
    loading,
    error,
    busy,
    actionError,
    // Ручные действия (только OWNER) — каждое создаёт новое SaleEvent; удаление продажи запрещено.
    correct: (amountMinor: number, reason: string) => act("correct", { amountMinor, reason }),
    partialRefund: (refundedAmountMinor: number, reason: string) => act("partial-refund", { refundedAmountMinor, reason }),
    refund: (reason: string) => act("refund", { reason }),
    cancel: (reason: string) => act("cancel", { reason }),
  };
}
