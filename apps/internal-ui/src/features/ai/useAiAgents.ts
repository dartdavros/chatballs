import { useCallback, useEffect, useState } from "react";

import { fetchAgentDirectory, type AgentRef } from "../agents/model";

export function useAiAgents() {
  const [agents, setAgents] = useState<AgentRef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const agentsResponse = await fetchAgentDirectory();
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
