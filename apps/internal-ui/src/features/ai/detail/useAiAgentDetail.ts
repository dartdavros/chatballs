import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import { fetchKnowledgeList, type KnowledgeItem } from "../knowledge/model";
import type { AiAgentDetail } from "./model";

type AgentDetailData = {
  agent: AiAgentDetail | null;
  library: KnowledgeItem[];
};

export function useAiAgentDetail(agentId: number | null) {
  const [data, setData] = useState<AgentDetailData>({ agent: null, library: [] });
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
      const [{ agent }, library] = await Promise.all([
        api<{ agent: AiAgentDetail }>(`/api/v1/ai/agents/${agentId}/`),
        fetchKnowledgeList(),
      ]);
      setData({ agent, library: library.items });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...data, loading, error, reload: load };
}
