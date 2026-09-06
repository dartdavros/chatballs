import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { Integration } from "../integrations/model";

// Интеграции грузятся один раз на весь экран «Настроек»: субменю показывает
// счётчики разделов «AI-провайдер» и «Интеграции» и красную точку ошибки
// (кадр N4), а сам раздел — таблицу.

export type IntegrationsState = {
  items: Integration[];
  loading: boolean;
  failed: boolean;
  reload: () => void;
};

export function useIntegrations(enabled: boolean): IntegrationsState {
  const [items, setItems] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const reload = useCallback(() => {
    if (!enabled) return;
    setFailed(false);
    api<{ items: Integration[] }>("/api/v1/integrations/")
      .then((payload) => setItems(payload.items))
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [enabled]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, loading, failed, reload };
}
