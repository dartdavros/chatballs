import { useEffect, useRef, useState } from "react";
import { t } from "../../../i18n";
import { candidates, searchLinks, updateLink, type Candidate, type EntityLink } from "./api";

export function useLinkSearch(link: EntityLink, conversation: number, done: () => void) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Candidate[] | null>(null);
  const [selected, select] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [runId, setRunId] = useState("");
  const generation = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => { generation.current++; clearTimeout(timer.current); }, [link.id, conversation]);
  const search = async () => {
    if (!query.trim() || busy) return;
    const token = ++generation.current;
    setBusy(true); setError(""); setItems(null); select("");
    const poll = async (run: string) => {
      if (token !== generation.current) return;
      try {
        const result = await candidates(link.id, conversation, run);
        if (token !== generation.current) return;
        if (result.state === "completed") { setItems(result.items); setBusy(false); }
        else if (["failed", "unknown", "cancelled", "approval"].includes(result.state)) { setError(t("runs.unavailable")); setBusy(false); }
        else timer.current = setTimeout(() => void poll(run), 1000);
      } catch { if (token === generation.current) { setError(t("runs.unavailable")); setBusy(false); } }
    };
    try { const run = await searchLinks(link.id, conversation, query, crypto.randomUUID()); setRunId(run.runId); await poll(run.runId); }
    catch { if (token === generation.current) { setError(t("runs.unavailable")); setBusy(false); } }
  };
  const apply = async () => {
    if (busy || !selected || !runId) return;
    setBusy(true); setError("");
    try { await updateLink(link, conversation, { action: "replace", searchRunId: runId, externalId: selected }); done(); }
    catch { setError(t("runs.unavailable")); }
    finally { setBusy(false); }
  };
  return { query, setQuery, items, selected, select, busy, error, search, apply };
}
