import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../../api/client";
import { loadAudit } from "./api";
import { EMPTY_AUDIT_QUERY, type AuditPayload, type AuditQuery } from "./model";

// Журнал аудита: фильтры и страница живут на сервере — журнал растёт без
// предела, и отдать его целиком нельзя. Поиск отложен, чтобы не слать запрос на
// каждую букву; смена любого фильтра возвращает на первую страницу — иначе
// человек остаётся на странице 7 отфильтрованного списка из двух событий.

const SEARCH_DELAY_MS = 300;

export function useAudit() {
  const [query, setQueryState] = useState<AuditQuery>(EMPTY_AUDIT_QUERY);
  const [payload, setPayload] = useState<AuditPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState(EMPTY_AUDIT_QUERY.q);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(query.q), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query.q]);

  // Ответы медленного запроса не должны затирать более свежий: считаем поколения.
  const generation = useRef(0);

  const effective: AuditQuery = { ...query, q: debouncedSearch };
  const { period, category, actor, result, page } = effective;

  const reload = useCallback(async () => {
    const current = ++generation.current;
    setLoading(true);
    setError("");
    try {
      const next = await loadAudit({ q: debouncedSearch, period, category, actor, result, page });
      if (current === generation.current) setPayload(next);
    } catch (loadError) {
      if (current !== generation.current) return;
      setError(loadError instanceof ApiError ? loadError.message : "Не удалось загрузить журнал");
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [debouncedSearch, period, category, actor, result, page]);

  useEffect(() => { void reload(); }, [reload]);

  const setQuery = useCallback((patch: Partial<AuditQuery>) => {
    setQueryState((prev) => ({
      ...prev,
      ...patch,
      // Страницу сбрасывает всё, кроме явной смены страницы.
      page: patch.page ?? 1,
    }));
  }, []);

  const reset = useCallback(() => setQueryState(EMPTY_AUDIT_QUERY), []);

  return { query, setQuery, reset, payload, loading, error, reload };
}
