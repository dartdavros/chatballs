import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { AiAgentDetail } from "./model";

export function useAiAgentDetail(agentId: number | null) {
  const [agent, setAgent] = useState<AiAgentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    if (!agentId) {
      setError(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(false);
    try {
      const payload = await api<{ agent: AiAgentDetail }>(`/api/v1/ai/agents/${agentId}/`);
      setAgent(payload.agent);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { agent, loading, error, reload: load };
}
