import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import { changedActions, loadActions, saveActions, type ActionMode, type AgentAction } from "./model";

export function useAgentActions(agent: number | null, enabled: boolean) {
  const [rows, setRows] = useState<AgentAction[] | null>(null);
  const [saved, setSaved] = useState<AgentAction[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);
  const generation = useRef(0);
  const reload = useCallback(async () => {
    if (agent === null || !enabled) return;
    const token = ++generation.current;
    setError("");
    try { const items = await loadActions(agent); if (token === generation.current) { setRows(items); setSaved(items); } }
    catch { if (token === generation.current) setError(t("runs.load_failed")); }
  }, [agent, enabled]);
  useEffect(() => { setRows(null); setSaved([]); setBusy(false); void reload(); return () => { generation.current++; }; }, [reload]);
  const dirty = rows !== null && changedActions(rows, saved).length > 0;
  const change = (id: string, mode: ActionMode) => { if (!saving.current) setRows(items => items?.map(row => row.id === id ? { ...row, mode } : row) ?? null); };
  const reset = () => { if (!saving.current) { setRows(saved); setError(""); } };
  const save = async () => {
    if (saving.current || !rows || agent === null) return false;
    saving.current = true;
    setBusy(true); setError("");
    const token = generation.current;
    try {
      const items = await saveActions(agent, changedActions(rows, saved));
      if (token === generation.current) { setSaved(items); setRows(items); return true; }
    } catch (caught) { if (token === generation.current) setError(caught instanceof ApiError ? caught.payload.detail ?? t("scenarios.request_failed") : t("scenarios.request_failed")); }
    finally { saving.current = false; if (token === generation.current) setBusy(false); }
    return false;
  };
  return { rows, busy, error, dirty, change, save, reload, reset };
}
