import { useCallback, useMemo, useState } from "react";

import { useDebounced } from "../../shared/useDebounced";
import { usePagedResource } from "../../shared/usePagedResource";
import { loadAudit } from "./api";
import { EMPTY_AUDIT_QUERY, type AuditPayload, type AuditQuery } from "./model";
import { t } from "../../i18n";

// Журнал аудита: фильтры и страница живут на сервере — журнал растёт без
// предела, и отдать его целиком нельзя. Страницей, отложенным поиском и
// защитой от гонок занимается общий usePagedResource: журнал был единственным
// списком со своей копией этой механики.

export function useAudit() {
  const [query, setQueryState] = useState<AuditQuery>(EMPTY_AUDIT_QUERY);
  const settledSearch = useDebounced(query.q);
  const filters = useMemo(
    () => ({
      q: settledSearch,
      period: query.period,
      category: query.category,
      actor: query.actor,
      result: query.result,
    }),
    [query.actor, query.category, query.period, query.result, settledSearch],
  );
  const load = useCallback(
    (page: number) => loadAudit({ ...filters, page }),
    [filters],
  );
  const journal = usePagedResource<AuditPayload>(load, filters, t("admin.could_not_load_log"));

  const setQuery = useCallback((patch: Partial<AuditQuery>) => {
    // Страницу двигает подвал списка, фильтры — состояние запроса; смена
    // фильтра сама возвращает на первую страницу (usePagedResource).
    if (patch.page !== undefined) {
      journal.setPage(patch.page);
      return;
    }
    setQueryState((prev) => ({ ...prev, ...patch }));
  }, [journal]);

  const reset = useCallback(() => setQueryState(EMPTY_AUDIT_QUERY), []);

  return {
    query: { ...query, page: journal.page },
    setQuery,
    reset,
    payload: journal.payload,
    loading: journal.loading,
    error: journal.errorText,
    reload: journal.reload,
  };
}
