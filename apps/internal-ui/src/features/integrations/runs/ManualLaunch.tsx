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
import { actionPresentationPath } from "./actionPickerModel";

type ManualLaunchProps = { action: ManualAction; conversationId: number; catalog: ManualCatalog; onClose: () => void; onRun: (id: string) => void;
  launchPending?: boolean; onBusyChange?: (busy: boolean) => void };

export function ManualLaunch(props: ManualLaunchProps) {
  return <ManualLaunchForm key={`${props.conversationId}:${props.action.kind}:${props.action.id}`} {...props} />;
}

function ManualLaunchForm({ action, conversationId, catalog, onClose, onRun, launchPending = false, onBusyChange }: ManualLaunchProps) {
  const [parameters, setParameters] = useState<Record<string, unknown>>(() => structuredClone(action.initialValues ?? {}));
  const [preview, setPreview] = useState<(PlanPreview & { stamp: string }) | null>(null);
  const [previewRevision, setPreviewRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");
  const [launchError, setLaunchError] = useState("");
  const [issues, setIssues] = useState<Array<{ path: string; message: string }>>([]);
  const [touched, setTouched] = useState<string[]>([]);
  const [triggerKey] = useState(() => crypto.randomUUID());
  const stamp = JSON.stringify(parameters);
  const generation = useRef(0);
  const active = useRef(false);
  const launching = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const locked = busy || launchPending;
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
  }, [action, conversationId, stamp, triggerKey, complete, previewRevision]); // parameter identity is represented by stamp
  const loadLookup = useCallback((connection: string, key: string) => manualLookup(action, conversationId, connection, key), [action, conversationId]);
  const launch = async () => {
    if (!active.current || !preview || preview.stamp !== stamp || locked || launching.current || unavailable) return;
    launching.current = true;
    setBusy(true); setError(""); setLaunchError("");
    onBusyChange?.(true);
    try { const run = await launchManual(action, conversationId, parameters, triggerKey, preview.confirmation); if (active.current) onRun(run.id); }
    catch (error) {
      if (active.current) {
        setLaunchError(error instanceof Error ? error.message : t("runs.unavailable"));
        // A rejected confirmation cannot be reused. Refresh only the plan;
        // execution still requires a new click with the same idempotency key.
        generation.current++;
        setPreview(null);
        setCalculating(true);
        setPreviewRevision(current => current + 1);
      }
    }
    finally { launching.current = false; onBusyChange?.(false); if (active.current) setBusy(false); }
  };
  const fieldIssues = [...issues, ...missing.filter(issue => touched.some(path => issue.path === path || issue.path.startsWith(`${path}.`)))];
  return <div className="run-launch"><div className="run-launch-content">
    {action.presentation && <p className="run-launch-source">{actionPresentationPath(action)}</p>}
    <div className="run-launch-plan"><strong>{t("runs.what_happens")}</strong>
    {(action.plan?.length ? action.plan : [preview?.operation ?? action.title]).map((step, index) => <p key={index}>{action.plan?.length ? `${index + 1}. ` : ""}{step}</p>)}</div>
    <LookupAccessContext.Provider value={loadLookup}><fieldset disabled={locked} className="scenario-fieldset run-launch-fields">
      {(action.parameters.fields ?? []).map(field => <div key={field.name}><ConstantValue field={field} value={parameters[field.name]} catalog={catalog} issues={fieldIssues}
        connection={String(action.connectionId ?? "")} onChange={value => {
          setTouched(current => current.includes(field.name) ? current : [...current, field.name]); setIssues([]); setLaunchError("");
          setParameters(current => ({ ...current, [field.name]: value }));
        }} />
      </div>)}</fieldset></LookupAccessContext.Provider>
    {action.kind === "scenario" && preview?.stamp === stamp && <RunValues schema={preview.inputSchema} value={preview.arguments} />}
    <div className="run-launch-notice" role="status">{error || launchError || (unavailable ? t("scenarios.control_unavailable") : "")}
      {calculating && <LoadingState variant="inline" />}</div>
    {preview?.note && <p className="run-launch-note">{preview.note}</p>}
    </div>
    <footer className="run-launch-footer"><div><Button variant="secondary" disabled={locked} onClick={onClose}>{t("runs.close")}</Button>
      <Button variant="primary" disabled={locked || calculating || !preview || preview.stamp !== stamp || unavailable} onClick={() => void launch()}>{t("runs.launch")}</Button></div></footer>
  </div>;
}
