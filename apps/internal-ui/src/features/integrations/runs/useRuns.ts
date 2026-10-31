import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { useRealtimeEvent } from "../../realtime/RealtimeProvider";
import { listRuns } from "./api";
import type { RunPage } from "./types";

export function useRuns(query: URLSearchParams) {
  const [data, setData] = useState<RunPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const version = useRef(0);
  const pending = useRef<number | null>(null);
  const serialized = query.toString();
  const load = useCallback(async (quiet = false) => {
    // A slow response must be allowed to finish. Polling must not invalidate
    // it every 15 seconds and leave the initial screen loading forever.
    if (quiet && pending.current === version.current) return;
    const token = ++version.current;
    pending.current = token;
    if (!quiet) setLoading(true);
    try {
      const result = await listRuns(new URLSearchParams(serialized));
      if (token === version.current) { setData(result); setError(""); }
    } catch { if (token === version.current) setError(t("runs.load_failed")); }
    finally { if (token === version.current) { pending.current = null; setLoading(false); } }
  }, [serialized]);
  useEffect(() => { void load(); return () => { version.current++; }; }, [load]);
  useRealtimeEvent("service_runs.changed", () => void load(true));
  useEffect(() => { const timer = window.setInterval(() => void load(true), 15000); return () => window.clearInterval(timer); }, [load]);
  return { data, loading, error, reload: load };
}
