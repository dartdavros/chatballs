import { useCallback, useEffect, useRef, useState } from "react";

import { fetchUpdate, installInProgress, type UpdateInfo } from "./api";

// Состояние обновления с опросом, пока идёт установка. Во время перезапуска
// бэкенд не отвечает — это не ошибка, а стадия: запросы продолжают уходить,
// пока новая версия не ответит статусом DONE или FAILED.

const POLL_INTERVAL_MS = 3000;

export function useUpdateInfo(enabled: boolean) {
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const wasInstalling = useRef(false);

  const load = useCallback(async () => {
    try {
      const next = await fetchUpdate();
      setInfo(next);
      setUnreachable(false);
    } catch {
      // Нет прав, сеть моргнула или бэкенд перезапускается.
      setUnreachable(true);
    }
  }, []);

  useEffect(() => {
    if (enabled) void load();
  }, [enabled, load]);

  const installing = installInProgress(info) || (unreachable && wasInstalling.current);
  if (installInProgress(info)) wasInstalling.current = true;

  useEffect(() => {
    if (!enabled || !installing) return undefined;
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [enabled, installing, load]);

  return { info, setInfo, reload: load, installing, unreachable, finished: wasInstalling.current && !installing };
}
