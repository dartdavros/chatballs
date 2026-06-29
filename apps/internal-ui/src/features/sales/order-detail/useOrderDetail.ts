import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { ApiOrder } from "../orders/model";

export function useOrderDetail(orderId: number | null) {
  const [order, setOrder] = useState<ApiOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (orderId === null) {
      setError(true);
      setLoading(false);
      return;
    }
    try {
      const { order: data } = await api<{ order: ApiOrder }>(`/api/v1/orders/${orderId}/`);
      setOrder(data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = useCallback(
    async (path: string, body?: object) => {
      if (orderId === null) return;
      setBusy(true);
      try {
        await api(`/api/v1/orders/${orderId}/${path}`, { method: "POST", body: body ? JSON.stringify(body) : undefined });
        await load();
      } catch {
        // оставляем текущее состояние; ошибка прав/сети
      } finally {
        setBusy(false);
      }
    },
    [orderId, load],
  );

  return {
    order,
    loading,
    error,
    busy,
    markPaid: () => act("mark-paid/"),
    cancel: () => act("cancel/"),
    setFulfillment: (status: string) => act("fulfillment/", { fulfillmentStatus: status }),
  };
}
