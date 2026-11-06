import { useCallback, useState } from "react";
import { api } from "../../../api/client";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { ConstantValue } from "../scenarios/ConstantValue";
import { LookupAccessContext } from "../services/lookupAccess";
import type { RunDetail, RunStep } from "./types";

export function ApprovalEditor({ run, step, busy, act }: { run: RunDetail; step: RunStep; busy: boolean;
  act: (action: string, body?: object) => Promise<RunDetail | null> }) {
  const [values, setValues] = useState<Record<string, unknown>>(() => structuredClone(step.arguments as Record<string, unknown>));
  const lookup = useCallback((_connection: string, key: string) => api<{ items: Array<{ value: string | number; label: string }> }>(
    `/api/v1/integrations/runs/${run.id}/approval-lookup/?${new URLSearchParams({ path: step.path, lookup: key })}`).then(r => r.items), [run.id, step.path]);
  return <div className="run-launch">
    <div className="run-launch-content"><LookupAccessContext.Provider value={lookup}><fieldset className="scenario-fieldset run-launch-fields" disabled={busy}>
      {step.inputSchema?.fields?.map(field => <ConstantValue key={field.name} field={field} value={values[field.name]}
        connection={String(step.connectionId ?? "")} catalog={{ files: run.files ?? [] }}
        onChange={value => setValues(current => ({ ...current, [field.name]: value }))} />)}
    </fieldset></LookupAccessContext.Provider></div>
    <footer><p>{t("agent_actions.edit_note")}</p><div>
      <Button variant="secondary" disabled={busy} onClick={() => setValues(structuredClone(step.arguments as Record<string, unknown>))}>{t("agent_actions.reset")}</Button>
      <Button variant="primary" disabled={busy} onClick={() => void act("revise", { path: step.path, digest: step.approvalDigest, editToken: step.editToken, arguments: values })}>{t("agent_actions.confirm_changes")}</Button>
    </div></footer>
  </div>;
}
