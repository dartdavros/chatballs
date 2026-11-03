import { useCallback, useEffect, useState } from "react";
import { t } from "../../../i18n";
import { useRealtimeEvent } from "../../realtime/RealtimeProvider";
import { listLinks, updateLink, type EntityLink } from "./api";

export function useEntityLinks(conversation: number | null) {
  const [data, setData] = useState<{ conversation: number; items: EntityLink[] } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const reload = useCallback(async () => {
    if (conversation === null) return;
    try { const value = await listLinks(conversation); setData({ conversation, items: value.items }); setError(""); }
    catch { setError(t("runs.load_failed")); }
  }, [conversation]);
  useEffect(() => { void reload(); }, [reload]);
  useRealtimeEvent("service_runs.changed", () => void reload());
  const unlink = async (link: EntityLink) => {
    if (conversation === null || busy) return;
    setBusy(true);
    try { await updateLink(link, conversation, { action: "unlink" }); await reload(); }
    catch { setError(t("runs.unavailable")); }
    finally { setBusy(false); }
  };
  return { links: data?.conversation === conversation ? data.items : null, error, busy, reload, unlink };
}
