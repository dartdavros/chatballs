import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import { loadActions, saveActions, type ActionMode, type AgentAction } from "./model";

export function useAgentActions(agent: number | null, enabled: boolean) {
  const [rows, setRows] = useState<AgentAction[] | null>(null);
  const [saved, setSaved] = useState<AgentAction[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const reload = useCallback(async () => {
    if (agent === null || !enabled) return;
    const token = ++generation.current;
    setError("");
    try { const items = await loadActions(agent); if (token === generation.current) { setRows(items); setSaved(items); } }
    catch { if (token === generation.current) setError(t("runs.load_failed")); }
  }, [agent, enabled]);
  useEffect(() => { setRows(null); setSaved([]); setBusy(false); void reload(); return () => { generation.current++; }; }, [reload]);
  const dirty = rows?.some(row => row.mode !== saved.find(old => old.id === row.id)?.mode) ?? false;
  const change = (id: string, mode: ActionMode) => setRows(items => items?.map(row => row.id === id ? { ...row, mode } : row) ?? null);
  const save = async () => {
    if (busy || !rows || agent === null) return;
    setBusy(true); setError("");
    const token = generation.current;
    try {
      const items = await saveActions(agent, rows.filter(row => row.mode !== saved.find(old => old.id === row.id)?.mode));
      if (token === generation.current) { setSaved(items); setRows(items); }
    } catch (caught) { if (token === generation.current) setError(caught instanceof ApiError ? caught.payload.detail ?? t("scenarios.request_failed") : t("scenarios.request_failed")); }
    finally { if (token === generation.current) setBusy(false); }
  };
  return { rows, busy, error, dirty, change, save, reload };
}
