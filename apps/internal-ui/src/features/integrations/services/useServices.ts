import { useCallback, useEffect, useState } from "react";

import { fetchAdapters, fetchConnections } from "./api";
import type { ServiceAdapter, ServiceConnection } from "./types";

/** Установленные адаптеры и подключения организации — вкладка «Сервисы». */
export function useServices() {
  const [adapters, setAdapters] = useState<ServiceAdapter[]>([]);
  const [connections, setConnections] = useState<ServiceConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [nextAdapters, nextConnections] = await Promise.all([fetchAdapters(), fetchConnections()]);
      setAdapters(nextAdapters);
      setConnections(nextConnections);
      setFailed(false);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  return { adapters, connections, loading, failed, reload };
}
