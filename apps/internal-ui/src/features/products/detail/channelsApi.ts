import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { Integration } from "../../integrations/model";

export type ProductChannel = {
  id: number;
  code: string;
  name: string;
  product: { code: string; name: string } | null;
  department: string | null;
  model: string;
  agentId: number | null;
  isActive: boolean;
};

export function useProductChannels(productCode: string) {
  const [channels, setChannels] = useState<ProductChannel[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ch, ig] = await Promise.all([
        api<{ items: ProductChannel[] }>("/api/v1/channels/"),
        api<{ items: Integration[] }>("/api/v1/integrations/"),
      ]);
      setChannels(ch.items.filter((channel) => channel.product?.code === productCode));
      setIntegrations(ig.items);
    } catch {
      setChannels([]);
      setIntegrations([]);
    } finally {
      setLoading(false);
    }
  }, [productCode]);

  useEffect(() => {
    void load();
  }, [load]);

  return { channels, integrations, loading, reload: load };
}
