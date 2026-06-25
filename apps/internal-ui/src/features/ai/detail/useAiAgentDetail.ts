import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { AiAgentDetail, AiReleaseFull, KnowledgeDoc, PromptDoc } from "./model";

type AgentDetailData = {
  agent: AiAgentDetail | null;
  releases: AiReleaseFull[];
  knowledge: KnowledgeDoc[];
  prompts: PromptDoc[];
};

export function useAiAgentDetail(agentId: number | null) {
  const [data, setData] = useState<AgentDetailData>({ agent: null, releases: [], knowledge: [], prompts: [] });
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
      const { agent } = await api<{ agent: AiAgentDetail }>(`/api/v1/ai/agents/${agentId}/`);
      const product = encodeURIComponent(agent.product.code);
      const [releases, knowledge, prompts] = await Promise.all([
        api<{ items: AiReleaseFull[] }>(`/api/v1/ai/releases/?product=${product}`),
        api<{ items: KnowledgeDoc[] }>(`/api/v1/ai/knowledge/?product=${product}`),
        api<{ items: PromptDoc[] }>(`/api/v1/ai/prompts/?product=${product}`),
      ]);
      setData({ agent, releases: releases.items, knowledge: knowledge.items, prompts: prompts.items });
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
