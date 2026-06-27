import { useCallback, useEffect, useState } from "react";

import { api } from "../../../api/client";
import type { AiReleaseFull, KnowledgeDoc, PromptDoc } from "../detail/model";

type ReleaseData = {
  knowledge: KnowledgeDoc[];
  prompts: PromptDoc[];
  release: AiReleaseFull | null;
  releases: AiReleaseFull[];
};

export function useProductAIRelease(releaseId: number | null) {
  const [data, setData] = useState<ReleaseData>({ knowledge: [], prompts: [], release: null, releases: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    if (!releaseId) {
      setError(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(false);
    try {
      const { release } = await api<{ release: AiReleaseFull }>(`/api/v1/ai/releases/${releaseId}/`);
      const channel = encodeURIComponent(release.channel.code);
      const [releases, knowledge, prompts] = await Promise.all([
        api<{ items: AiReleaseFull[] }>(`/api/v1/ai/releases/?channel=${channel}`),
        api<{ items: KnowledgeDoc[] }>("/api/v1/ai/knowledge/"),
        api<{ items: PromptDoc[] }>("/api/v1/ai/prompts/"),
      ]);
      setData({ release, releases: releases.items, knowledge: knowledge.items, prompts: prompts.items });
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [releaseId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { ...data, loading, error, reload: load };
}
