import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../../api/client";
import { t } from "../../../../i18n";
import { fetchCatalog, fetchExchange, saveExchange } from "../../scenarios/api";
import type { EditorCatalog, ExchangeSettings, Issue } from "../../scenarios/types";

export function useServiceExchange(connection: number) {
  const [catalog, setCatalog] = useState<EditorCatalog | null>(null);
  const [settings, setSettings] = useState<ExchangeSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    setLoading(true); setError("");
    try { const [metadata, current] = await Promise.all([fetchCatalog(), fetchExchange(connection)]); setCatalog(metadata); setSettings(current); }
    catch { setError(t("services.load_failed")); } finally { setLoading(false); }
  }, [connection]);
  useEffect(() => { void reload(); }, [reload]);
  async function save(next: ExchangeSettings) {
    setSaving(true); setError("");
    try { setSettings(await saveExchange(connection, next)); return true; }
    catch (caught) {
      const body = caught instanceof ApiError ? caught.payload as { detail?: string; issues?: Issue[] } : null;
      setError(caught instanceof ApiError && caught.status === 409 ? t("scenarios.exchange_conflict_error") : body?.detail ?? body?.issues?.[0]?.message ?? t("services.request_failed")); return false;
    } finally { setSaving(false); }
  }
  return { catalog, settings, loading, saving, error, reload, save };
}
