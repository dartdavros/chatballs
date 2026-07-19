import { useCallback, useEffect, useState } from "react";

import { fetchKnowledgeCategories, type KnowledgeCategory } from "./model";

export function useKnowledgeCategories() {
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const payload = await fetchKnowledgeCategories();
      setCategories(payload.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { categories, error, loading, reload: load };
}
