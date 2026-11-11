import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { useRealtimeEvent } from "../../realtime/RealtimeProvider";
import { listRuns } from "./api";
import type { RunSummary } from "./types";

export function useConversationRunHistory(conversationId: number | null) {
  const contextRef = useRef({ conversationId });
  if (contextRef.current.conversationId !== conversationId) contextRef.current = { conversationId };
  const context = contextRef.current;
  const active = useRef(false);
  const [data, setData] = useState<{ context: typeof context; rows: RunSummary[]; count: number } | null>(null);
  const [status, setStatus] = useState({ context, loading: false, error: "" });
  const generation = useRef(0);
  const pending = useRef<number | null>(null);
  const pages = useRef(1);
  const refresh = useCallback(async (quiet = true) => {
    if (!active.current || contextRef.current !== context || context.conversationId === null) return;
    if (quiet && pending.current === generation.current) return;
    const token = ++generation.current;
    const current = () => active.current && contextRef.current === context && token === generation.current;
    pending.current = token;
    if (!quiet) setStatus({ context, loading: true, error: "" });
    try {
      const runs = await Promise.all(Array.from({ length: pages.current }, (_, index) => listRuns(
        new URLSearchParams({ conversation: String(context.conversationId), page: String(index + 1) }))));
      if (current()) {
        setData({ context, rows: runs.flatMap(page => page.items), count: runs[0].count });
        setStatus({ context, loading: false, error: "" });
      }
    } catch { if (current()) setStatus({ context, loading: false, error: t("runs.load_failed") }); }
    finally { if (current()) pending.current = null; }
  }, [context]);
  useEffect(() => {
    active.current = true;
    pages.current = 1;
    void refresh(false);
    return () => { active.current = false; generation.current++; };
  }, [refresh]);
  useRealtimeEvent("service_runs.changed", () => void refresh());
  useEffect(() => { const timer = setInterval(() => void refresh(), 15000); return () => clearInterval(timer); }, [refresh]);
  const current = data?.context === context ? data : null;
  const loading = status.context === context && status.loading;
  const loadOlder = async () => {
    if (!active.current || contextRef.current !== context || !current || loading || current.rows.length >= current.count) return;
    pages.current++;
    await refresh(false);
  };
  return { runs: current?.rows ?? [], loading, error: status.context === context ? status.error : "",
    hasMore: (current?.rows.length ?? 0) < (current?.count ?? 0), loadOlder, refresh };
}
