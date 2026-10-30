import { useCallback, useEffect, useState } from "react";

import { checkConnection, deleteConnection, fetchAdapters, fetchConnection, serviceFailure, updateConnection } from "../api";
import { takeConnected } from "../connectedNotice";
import { adapterOf } from "../model";
import type { ServiceAdapter, ServiceConnection, ServiceFailure } from "../types";

/** Карточка подключения сервиса: данные и действия (кадры «Карточка · …»). */
export function useServiceCard(id: number) {
  const [connection, setConnection] = useState<ServiceConnection | null>(null);
  const [adapters, setAdapters] = useState<ServiceAdapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [checking, setChecking] = useState(false);
  const [failure, setFailure] = useState<ServiceFailure | null>(null);
  const [justConnected, setJustConnected] = useState(() => takeConnected(id));

  const load = useCallback(async () => {
    try {
      const [nextConnection, nextAdapters] = await Promise.all([fetchConnection(id), fetchAdapters()]);
      setConnection(nextConnection);
      setAdapters(nextAdapters);
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  async function act(action: () => Promise<ServiceConnection>) {
    setFailure(null);
    try {
      setConnection(await action());
    } catch (error) {
      setFailure(serviceFailure(error));
      await load();
    }
  }

  return {
    connection,
    adapter: adapterOf(adapters, connection),
    loading,
    failed,
    checking,
    failure,
    justConnected,
    hideNotice: () => setJustConnected(false),
    reload: load,
    rename: (name: string) => act(() => updateConnection(id, { name })),
    setActive: (isActive: boolean) => act(() => updateConnection(id, { isActive })),
    check: async () => {
      setChecking(true);
      await act(() => checkConnection(id));
      setChecking(false);
    },
    remove: () => deleteConnection(id),
  };
}
