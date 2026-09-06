import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { ContactCardFields } from "../../conversations/ContactEditForm";
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

  async function save(fields: ContactCardFields) {
    if (contactId === null) return;
    const data = await api<{ client: ApiClientDetail }>(`/api/v1/conversations/clients/${contactId}/`, { method: "PATCH", body: JSON.stringify(fields) });
    setClient(toClientDetailVm(data.client));
  }

  return { client, loading, error, save };
}
