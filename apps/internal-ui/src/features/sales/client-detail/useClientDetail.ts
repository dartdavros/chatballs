import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { toClientDetailVm, type ApiClientDetail, type ClientDetailVm } from "./model";

export function useClientDetail(contactId: number | null) {
  const [client, setClient] = useState<ClientDetailVm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (contactId === null) {
      setError(true);
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    setError(false);
    api<{ client: ApiClientDetail }>(`/api/v1/conversations/clients/${contactId}/`)
      .then((data) => {
        if (active) setClient(toClientDetailVm(data.client));
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
  }, [contactId]);

  return { client, loading, error };
}
