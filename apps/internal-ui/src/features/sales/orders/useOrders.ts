import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { ApiOrder } from "./model";

export function useOrders() {
  const [orders, setOrders] = useState<ApiOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    api<{ items: ApiOrder[] }>("/api/v1/orders/")
      .then((data) => {
        if (active) setOrders(data.items);
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
  }, []);

  return { orders, loading, error };
}
