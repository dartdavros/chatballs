import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AiAgent } from "./model";

export function useAiAgents() {
  const [agents, setAgents] = useState<AiAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const agentsResponse = await api<{ items: AiAgent[] }>("/api/v1/ai/agents/");
      setAgents(agentsResponse.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { agents, loading, error, reload: load };
}
