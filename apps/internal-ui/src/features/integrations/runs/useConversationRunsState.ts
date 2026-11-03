import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { useRealtimeEvent } from "../../realtime/RealtimeProvider";
import { getManualActions, listRuns } from "./api";
import type { ManualAction, ManualCatalog, RunSummary } from "./types";
import type { EntityLink } from "../entity-links/api";

export function useConversationRunsState(conversationId: number | null) {
  const [catalog, setCatalog] = useState<(ManualCatalog & { conversationId: number }) | null>(null);
  const [data, setData] = useState<{ conversationId: number; rows: RunSummary[]; count: number } | null>(null);
  const [sheet, setSheet] = useState<{ conversationId: number; action?: ManualAction; runId?: string; link?: EntityLink } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ conversationId: number; text: string } | null>(null);
  const generation = useRef(0);
  const pending = useRef<number | null>(null);
  const pages = useRef(1);
  const refresh = useCallback(async (quiet = true) => {
    if (conversationId === null) { setLoading(false); return; }
    if (quiet && pending.current === generation.current) return;
    const token = ++generation.current;
    pending.current = token;
    if (!quiet) setLoading(true);
    try {
      const [actions, runs] = await Promise.all([getManualActions(conversationId), Promise.all(
        Array.from({ length: pages.current }, (_, index) => listRuns(new URLSearchParams({ conversation: String(conversationId), page: String(index + 1) }))))]);
      if (token === generation.current) {
        setCatalog({ ...actions, conversationId });
        setData({ conversationId, rows: runs.flatMap(page => page.items), count: runs[0].count });
        setError(null);
      }
    } catch { if (token === generation.current) setError({ conversationId, text: t("runs.load_failed") }); }
    finally { if (token === generation.current) { pending.current = null; setLoading(false); } }
  }, [conversationId]);
  useEffect(() => { pages.current = 1; void refresh(false); return () => { generation.current++; }; }, [refresh]);
  useRealtimeEvent("service_runs.changed", () => void refresh());
  useEffect(() => { const timer = setInterval(() => void refresh(), 15000); return () => clearInterval(timer); }, [refresh]);
  const current = data?.conversationId === conversationId ? data : null;
  const loadOlder = async () => {
    if (!current || loading || current.rows.length >= current.count) return;
    pages.current++;
    await refresh(false);
  };
  return { conversationId, catalog: catalog?.conversationId === conversationId ? catalog : null,
    runs: current?.rows ?? [], loading, error: error?.conversationId === conversationId ? error.text : "",
    hasMore: (current?.rows.length ?? 0) < (current?.count ?? 0), loadOlder, refresh,
    sheet: sheet?.conversationId === conversationId ? sheet : null,
    openAction: (action: ManualAction) => { if (conversationId !== null) setSheet({ conversationId, action }); },
    openRun: (runId: string) => { if (conversationId !== null) setSheet({ conversationId, runId }); },
    openLink: (link: EntityLink) => { if (conversationId !== null) setSheet({ conversationId, link }); }, close: () => setSheet(null) };
}
