import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchKnowledgeList, type KnowledgeItem } from "./model";

export function useKnowledgeLibrary() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");

  const reload = useCallback(async () => {
    setError(false);
    try {
      const payload = await fetchKnowledgeList();
      setItems(payload.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const filteredItems = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter(
      (item) => item.title.toLowerCase().includes(needle)
        || item.description.toLowerCase().includes(needle),
    );
  }, [items, query]);

  return {
    error,
    filteredItems,
    loading,
    query,
    reload,
    setQuery,
  };
}
