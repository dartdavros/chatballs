import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { useRealtimeEvent } from "../../realtime/RealtimeProvider";
import { controlRun, getRun } from "./api";
import type { RunDetail } from "./types";

export function useRunDetail(id: string) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [changed, setChanged] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const load = useCallback(async () => {
    const token = ++generation.current; setLoading(true);
    try { const result = await getRun(id); if (token === generation.current) { setRun(result); setError(""); setChanged(false); } }
    catch { if (token === generation.current) setError(t("runs.load_failed")); }
    finally { if (token === generation.current) setLoading(false); }
  }, [id]);
  useEffect(() => { setRun(null); void load(); return () => { generation.current++; }; }, [load]);
  useRealtimeEvent("service_runs.changed", () => setChanged(true));
  useEffect(() => { const timer = window.setInterval(() => setChanged(true), 15000); return () => clearInterval(timer); }, []);
  const act = async (action: string, body: object = {}) => {
    if (busy) return null;
    setBusy(true); setError("");
    try { const result = await controlRun(id, action, body); setRun(result); setChanged(false); return result; }
    catch (error) { setError(error instanceof Error ? error.message : t("runs.unavailable")); return null; }
    finally { setBusy(false); }
  };
  return { run, loading, busy, changed, error, load, act };
}
