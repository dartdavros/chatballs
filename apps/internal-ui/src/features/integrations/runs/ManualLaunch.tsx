import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { LoadingState } from "../../../shared/ui";
import { ConstantValue } from "../scenarios/ConstantValue";
import { unavailableField } from "../scenarios/controlModel";
import { LookupAccessContext } from "../services/lookupAccess";
import { launchManual, manualLookup, previewManual } from "./api";
import { RunValues } from "./RunValues";
import type { ManualAction, ManualCatalog, PlanPreview } from "./types";

export function ManualLaunch({ action, conversationId, catalog, onClose, onRun }: { action: ManualAction; conversationId: number; catalog: ManualCatalog; onClose: () => void; onRun: (id: string) => void }) {
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [preview, setPreview] = useState<(PlanPreview & { stamp: string }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");
  const [issues, setIssues] = useState<Array<{ path: string; message: string }>>([]);
  const [triggerKey] = useState(() => crypto.randomUUID());
  const stamp = JSON.stringify(parameters);
  const generation = useRef(0);
  const unavailable = unavailableField(action.parameters);
  useEffect(() => {
    const token = ++generation.current;
    setCalculating(true); setError("");
    const timer = setTimeout(() => { void previewManual(action, conversationId, parameters, triggerKey)
      .then(plan => { if (token === generation.current) { setPreview({ ...plan, stamp }); setIssues([]); } })
      .catch(error => { if (token === generation.current) { setPreview(null); setError(error instanceof Error ? error.message : t("runs.unavailable"));
        setIssues(error instanceof ApiError && Array.isArray(error.payload.issues) ? error.payload.issues : []); } })
      .finally(() => { if (token === generation.current) setCalculating(false); }); }, 300);
    return () => { generation.current++; clearTimeout(timer); };
  }, [action, conversationId, stamp, triggerKey]); // parameter identity is represented by stamp
  const loadLookup = useCallback((connection: string, key: string) => manualLookup(action, conversationId, connection, key), [action, conversationId]);
  const launch = async () => {
    if (!preview || preview.stamp !== stamp || busy || unavailable) return;
    setBusy(true); setError("");
    try { const run = await launchManual(action, conversationId, parameters, triggerKey, preview.confirmation); onRun(run.id); }
    catch (error) { setError(error instanceof Error ? error.message : t("runs.unavailable")); }
    finally { setBusy(false); }
  };
  return <div className="run-launch"><div className="run-launch-plan"><strong>{t("runs.what_happens")}</strong><p>{preview?.operation ?? action.title}</p></div>
    <LookupAccessContext.Provider value={loadLookup}><fieldset disabled={busy} className="scenario-fieldset run-launch-fields">
      {(action.parameters.fields ?? []).map(field => <div key={field.name}><ConstantValue field={field} value={parameters[field.name]} catalog={catalog}
        connection={String(action.connectionId ?? "")} onChange={value => setParameters(current => ({ ...current, [field.name]: value }))} />
        {issues.filter(issue => issue.path === field.name || issue.path.startsWith(`${field.name}.`)).map(issue => <small key={issue.path} className="form-field-error">{issue.message}</small>)}
      </div>)}</fieldset></LookupAccessContext.Provider>
    {action.kind === "scenario" && preview?.stamp === stamp && <RunValues schema={preview.inputSchema} value={preview.arguments} />}
    <div className="run-launch-notice" role="status">{calculating ? <LoadingState variant="inline" /> : error || (unavailable ? t("scenarios.control_unavailable") : "")}</div>
    <footer><p>{preview?.note}</p><div><Button variant="secondary" disabled={busy} onClick={onClose}>{t("runs.close")}</Button>
      <Button variant="primary" disabled={busy || calculating || !preview || preview.stamp !== stamp || unavailable} onClick={() => void launch()}>{t("runs.launch")}</Button></div></footer>
  </div>;
}
