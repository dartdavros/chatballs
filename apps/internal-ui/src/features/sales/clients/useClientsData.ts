import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { toSalesClient, type ApiClient, type SalesClient } from "./model";

export function useClientsData() {
  const [clients, setClients] = useState<SalesClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    api<{ items: ApiClient[] }>("/api/v1/conversations/clients/")
      .then((data) => {
        if (active) setClients(data.items.map(toSalesClient));
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

  return { clients, loading, error };
}
