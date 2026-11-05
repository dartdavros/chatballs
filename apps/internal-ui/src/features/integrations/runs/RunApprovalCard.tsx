import { fmt, t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { LoadingState } from "../../../shared/ui";
import { RunStatus } from "./RunStatus";
import { RunValues } from "./RunValues";
import { useRunDetail } from "./useRunDetail";

export function RunApprovalCard({ id, onDetails }: { id: string; onDetails: () => void }) {
  const state = useRunDetail(id);
  const run = state.run;
  const step = run?.steps.find(row => row.state === "approval");
  if (!run) return <article className="run-feed-card run-detail-state">{state.error || <LoadingState variant="inline" />}</article>;
  const canApprove = run.controls.includes("approve") && !state.changed && !step?.editing;
  return <article className="run-feed-card is-ai">
    <header><Icon name="robot" size={17} /><strong>{run.name}</strong><RunStatus state={run.state} label={run.stateLabel} /></header>
    <small>{t("runs.run_label", { number: fmt.number(run.number) })} · {run.initiator}</small>
    {step && <><RunValues schema={step.inputSchema} value={step.arguments} fileNames={step.fileNames} />
      {(!step.editing || step.editToken) && <p>{t(step.editing ? "agent_actions.editing" : "agent_actions.confirm_note")}</p>}
      {step.deadline && <p>{t("agent_actions.valid_until", { date: fmt.shortDateTime(step.deadline) })}</p>}
      {canApprove && <div className="run-detail-actions">
        <Button variant="primary" disabled={state.busy} onClick={() => void state.act("approve", { path: step.path, digest: step.approvalDigest })}>{t("runs.approve")}</Button>
        <Button variant="secondary" disabled={state.busy} onClick={async () => { if (await state.act("edit", { path: step.path, digest: step.approvalDigest })) onDetails(); }}>{t("common.edit")}</Button>
        <Button variant="secondary" disabled={state.busy} onClick={() => void state.act("cancel")}>{t("runs.reject")}</Button>
      </div>}
      {!run.controls.includes("approve") && <p>{t("agent_actions.approver_note")}</p>}
    </>}
    {state.error && <p className="run-step-error" role="alert">{state.error}</p>}
    {state.changed && <button className="link" type="button" onClick={() => void state.load()}>{t("runs.retry")}</button>}
    <footer><button className="link" type="button" onClick={onDetails}>{t("runs.details")}</button><time>{fmt.time(run.createdAt)}</time></footer>
  </article>;
}
