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
import { requiredIssues } from "./launchFields";

type ManualLaunchProps = { action: ManualAction; conversationId: number; catalog: ManualCatalog; onClose: () => void; onRun: (id: string) => void };

export function ManualLaunch(props: ManualLaunchProps) {
  return <ManualLaunchForm key={`${props.conversationId}:${props.action.kind}:${props.action.id}`} {...props} />;
}

function ManualLaunchForm({ action, conversationId, catalog, onClose, onRun }: ManualLaunchProps) {
  const [parameters, setParameters] = useState<Record<string, unknown>>(() => structuredClone(action.initialValues ?? {}));
  const [preview, setPreview] = useState<(PlanPreview & { stamp: string }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");
  const [issues, setIssues] = useState<Array<{ path: string; message: string }>>([]);
  const [touched, setTouched] = useState<string[]>([]);
  const [triggerKey] = useState(() => crypto.randomUUID());
  const stamp = JSON.stringify(parameters);
  const generation = useRef(0);
  const unavailable = unavailableField(action.parameters);
  const missing = requiredIssues(action.parameters, parameters);
  const complete = missing.length === 0;
  useEffect(() => {
    const token = ++generation.current;
    setError("");
    if (!complete) { setPreview(null); setCalculating(false); return; }
    setCalculating(true);
    const timer = setTimeout(() => { void previewManual(action, conversationId, parameters, triggerKey)
      .then(plan => { if (token === generation.current) { setPreview({ ...plan, stamp }); setIssues([]); } })
      .catch(error => { if (token === generation.current) { setPreview(null); setError(error instanceof Error ? error.message : t("runs.unavailable"));
        setIssues(error instanceof ApiError && Array.isArray(error.payload.issues) ? error.payload.issues : []); } })
      .finally(() => { if (token === generation.current) setCalculating(false); }); }, 300);
    return () => { generation.current++; clearTimeout(timer); };
  }, [action, conversationId, stamp, triggerKey, complete]); // parameter identity is represented by stamp
  const loadLookup = useCallback((connection: string, key: string) => manualLookup(action, conversationId, connection, key), [action, conversationId]);
  const launch = async () => {
    if (!preview || preview.stamp !== stamp || busy || unavailable) return;
    setBusy(true); setError("");
    try { const run = await launchManual(action, conversationId, parameters, triggerKey, preview.confirmation); onRun(run.id); }
    catch (error) { setError(error instanceof Error ? error.message : t("runs.unavailable")); }
    finally { setBusy(false); }
  };
  const fieldIssues = [...issues, ...missing.filter(issue => touched.some(path => issue.path === path || issue.path.startsWith(`${path}.`)))];
  return <div className="run-launch"><div className="run-launch-content"><div className="run-launch-plan"><strong>{t("runs.what_happens")}</strong>
    {(action.plan?.length ? action.plan : [preview?.operation ?? action.title]).map((step, index) => <p key={index}>{action.plan?.length ? `${index + 1}. ` : ""}{step}</p>)}</div>
    <LookupAccessContext.Provider value={loadLookup}><fieldset disabled={busy} className="scenario-fieldset run-launch-fields">
      {(action.parameters.fields ?? []).map(field => <div key={field.name}><ConstantValue field={field} value={parameters[field.name]} catalog={catalog} issues={fieldIssues}
        connection={String(action.connectionId ?? "")} onChange={value => {
          setTouched(current => current.includes(field.name) ? current : [...current, field.name]); setIssues([]);
          setParameters(current => ({ ...current, [field.name]: value }));
        }} />
      </div>)}</fieldset></LookupAccessContext.Provider>
    {action.kind === "scenario" && preview?.stamp === stamp && <RunValues schema={preview.inputSchema} value={preview.arguments} />}
    <div className="run-launch-notice" role="status">{calculating ? <LoadingState variant="inline" /> : error || (unavailable ? t("scenarios.control_unavailable") : "")}</div>
    {preview?.note && <p className="run-launch-note">{preview.note}</p>}
    </div>
    <footer className="run-launch-footer"><div><Button variant="secondary" disabled={busy} onClick={onClose}>{t("runs.close")}</Button>
      <Button variant="primary" disabled={busy || calculating || !preview || preview.stamp !== stamp || unavailable} onClick={() => void launch()}>{t("runs.launch")}</Button></div></footer>
  </div>;
}
