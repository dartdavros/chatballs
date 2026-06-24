import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AiAgent, AiRelease } from "./model";

export function useAiAgents() {
  const [agents, setAgents] = useState<AiAgent[]>([]);
  const [releases, setReleases] = useState<AiRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [agentsResponse, releasesResponse] = await Promise.all([
        api<{ items: AiAgent[] }>("/api/v1/ai/agents/"),
        api<{ items: AiRelease[] }>("/api/v1/ai/releases/"),
      ]);
      setAgents(agentsResponse.items);
      setReleases(releasesResponse.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { agents, releases, loading, error, reload: load };
}
