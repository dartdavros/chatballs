import { useEffect, useState } from "react";
import { fmt, t, tn } from "../../../i18n";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { SelectField } from "../../../shared/form-controls";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { getRetention, saveRetention } from "./api";
import type { RetentionPolicy } from "./types";
import "./runs.css";

export function RunRetention() {
  const [saved, setSaved] = useState<RetentionPolicy | null>(null);
  const [draft, setDraft] = useState<RetentionPolicy | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { let active = true; getRetention().then(policy => { if (active) { setSaved(policy); setDraft(policy); } })
    .catch(() => { if (active) setError(t("runs.load_failed")); }); return () => { active = false; }; }, []);
  const persist = async (confirmed: boolean) => {
    if (!draft || busy) return;
    setBusy(true); setError("");
    try { const policy = await saveRetention(draft, confirmed); setSaved(policy); setDraft(policy); setConfirming(false); setMessage(t("runs.saved")); }
    catch (error) { setError(error instanceof Error ? error.message : t("runs.unavailable")); }
    finally { setBusy(false); }
  };
  const shortening = Boolean(saved && draft && (draft.stepDays < saved.stepDays || draft.journalDays < saved.journalDays));
  const dirty = Boolean(saved && draft && (draft.stepDays !== saved.stepDays || draft.journalDays !== saved.journalDays));
  return <section className="run-retention"><h3>{t("runs.retention_title")}</h3><p>{t("runs.retention_text")}</p>
    {!draft ? <div className="run-retention-state">{error || <LoadingState />}</div> : <>
      <div className="run-retention-row"><div><strong>{t("runs.history_label")}</strong><small>{t("runs.history_help")}</small></div>
        <SelectField label="" value={String(draft.journalDays)} disabled={busy} options={[30, 90, 180, 365].map(count => [String(count), count === 365 ? t("runs.one_year") : tn("runs.days", count, { count: fmt.number(count) })])}
          onChange={value => setDraft({ ...draft, journalDays: Number(value), stepDays: Math.min(draft.stepDays, Number(value)) })} /></div>
      <div className="run-retention-row"><div><strong>{t("runs.step_label")}</strong><small>{t("runs.step_help")}</small></div>
        <SelectField label="" value={String(draft.stepDays)} disabled={busy} options={[3, 7, 14, 30].filter(n => n <= draft.journalDays).map(count => [String(count), tn("runs.days", count, { count: fmt.number(count) })])}
          onChange={value => setDraft({ ...draft, stepDays: Number(value) })} /></div>
      {dirty && shortening && <div className="run-notice is-warning">{t("runs.retention_shorten_text")}</div>}
      <div className="run-retention-footer"><span>{error || (saved?.effectiveAt ? t("runs.retention_pending", { when: fmt.shortDateTime(saved.effectiveAt) }) : message)}</span>
        <Button variant="primary" disabled={!dirty || busy} onClick={() => shortening ? setConfirming(true) : void persist(false)}>{t("runs.save")}</Button></div>
    </>}
    <DecisionDialog open={confirming} title={t("runs.retention_shorten")} description={t("runs.retention_shorten_text")} icon="warning" tone="warning" onClose={() => setConfirming(false)} actions={<>
      <Button variant="secondary" onClick={() => setConfirming(false)}>{t("runs.close")}</Button><Button variant="primary" disabled={busy} onClick={() => void persist(true)}>{t("runs.save")}</Button></>} />
  </section>;
}
