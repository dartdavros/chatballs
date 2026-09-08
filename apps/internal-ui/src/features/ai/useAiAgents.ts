import { useCallback, useEffect, useState } from "react";

import { fetchAllAgents, type AgentCard } from "../agents/model";

export function useAiAgents() {
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const agentsResponse = await fetchAllAgents();
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
