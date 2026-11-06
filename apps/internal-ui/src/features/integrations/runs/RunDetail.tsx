import { useState } from "react";
import { Dropdown } from "antd";
import { fmt, t } from "../../../i18n";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { RunStatus } from "./RunStatus";
import { RunValues } from "./RunValues";
import { useRunDetail } from "./useRunDetail";
import { ApprovalEditor } from "./ApprovalEditor";
import { RunConflict } from "./RunConflict";

export function RunDetail({ id, onBack, inChat = false, onRepeated }: { id: string; onBack: () => void; inChat?: boolean; onRepeated?: (id: string) => void }) {
  const state = useRunDetail(id);
  const [repeat, setRepeat] = useState<string | null>(null);
  const run = state.run;
  if (!run) return <div className="run-detail-state">{state.loading ? <LoadingState /> : <EmptyState title={state.error} />}</div>;
  const approval = run.steps.find(step => step.state === "approval" && step.approvalDigest);
  return <div className="run-detail">
    <button className="link is-muted has-icon" type="button" onClick={onBack}><Icon name="chevronLeft" size={14} />{t(inChat ? "runs.back_chat" : "runs.back")}</button>
    <header className="run-detail-head"><div><div className="run-title"><h2>{run.name}</h2><RunStatus state={run.state} label={run.stateLabel} /></div>
      <p>{t("runs.run_label", { number: fmt.number(run.number) })} · {fmt.shortDateTime(run.createdAt)}</p></div>
      <div className="run-detail-actions">{run.controls.includes("reconcile") && <Button variant="secondary" disabled={state.busy} onClick={() => void state.act("reconcile", { path: run.reconcilePath })}>{t("runs.reconcile")}</Button>}
        {!run.dataCleared && <Dropdown overlayClassName="app-dropdown" placement="bottomRight" trigger={["click"]} menu={{ items: [
          { key: "cancel", label: <button type="button" disabled={!run.controls.includes("cancel")}>{t("runs.cancel")}</button>, disabled: !run.controls.includes("cancel") },
          { key: "repeat", label: <button type="button" disabled={!run.controls.includes("repeat")}>{t("runs.repeat")}</button>, disabled: !run.controls.includes("repeat") },
        ], onClick: ({ key }) => key === "repeat" ? setRepeat(crypto.randomUUID()) : void state.act("cancel") }}>
          <button type="button" className="row-menu-button" aria-label={t("runs.actions")} disabled={state.busy}><Icon name="more" size={17} /></button>
        </Dropdown>}
      </div>
    </header>
    {state.changed && <div className="run-notice"><span>{t("runs.journal_changed")}</span><button type="button" className="link" onClick={() => void state.load()}>{t("runs.retry")}</button></div>}
    {state.error && <div className="run-notice is-error" role="alert">{state.error}</div>}
    {run.dataCleared && <div className="run-notice">{t("runs.cleared")}</div>}
    {run.state === "unknown" && <div className="run-notice is-warning">{t("runs.unknown_text")}</div>}
    {run.cancelRequested && !run.finishedAt && <div className="run-notice is-warning">{t("runs.cancel_requested")}</div>}
    {run.ai && approval?.editToken && <ApprovalEditor key={approval.editToken} run={run} step={approval} busy={state.busy || state.changed} act={state.act} />}
    {run.conflict && <RunConflict key={run.conflict.digest} conflict={run.conflict} disabled={state.busy || state.changed}
      apply={choices => void state.act("resolve", { digest: run.conflict!.digest, choices })} />}
    <dl className="run-meta"><div><dt>{t("runs.initiator")}</dt><dd>{run.initiator}</dd></div>
      <div><dt>{t("runs.where")}</dt><dd>{run.conversationId ? t("runs.conversation", { number: fmt.number(run.conversationId) }) : "—"}</dd></div>
      <div><dt>{t("runs.started")}</dt><dd>{fmt.shortDateTime(run.createdAt)}</dd></div>
      <div><dt>{t("runs.ended")}</dt><dd>{run.finishedAt ? fmt.shortDateTime(run.finishedAt) : "—"}</dd></div>
      <div><dt>{t("runs.definition_version")}</dt><dd>{run.definitionUpdatedAt ? fmt.shortDateTime(run.definitionUpdatedAt) : "—"}</dd></div>
      <div><dt>{t("runs.connections")}</dt><dd>{run.connection || "—"}</dd></div></dl>
    <section className="run-steps"><h3>{t("runs.steps")}</h3>{run.steps.map(step => <div className="run-step" key={step.path}>
      <div className="run-step-title"><strong>{step.title}</strong><RunStatus state={step.state} label={step.stateLabel} /></div>
      {step.scope?.map((scope, index) => <p key={index}>{t(scope.kind === "iteration" ? "runs.iteration_number" : "runs.branch_number", { number: fmt.number(scope.number) })}</p>)}
      {step.prompt && <p>{step.prompt}</p>}
      {step.error && <p className="run-step-error">{step.error}</p>}
      {step.deadline && <p>{fmt.shortDateTime(step.deadline)}</p>}
      {!run.dataCleared && <><RunValues schema={step.inputSchema} value={step.arguments} fileNames={step.fileNames} /><RunValues schema={step.outputSchema} value={step.result} fileNames={step.fileNames} /></>}
      {step.decision && <div className="run-detail-actions"><Button variant="primary" disabled={state.busy || state.changed}
        onClick={() => void state.act("decide", { path: step.path, ...step.decision, accepted: true })}>{t("runs.approve")}</Button>
        <Button variant="secondary" disabled={state.busy || state.changed}
          onClick={() => void state.act("decide", { path: step.path, ...step.decision, accepted: false })}>{t("runs.reject")}</Button></div>}
    </div>)}</section>
    {approval?.approvalDigest && run.controls.includes("approve") && !approval.editing && <div className="run-detail-actions"><Button variant="primary" disabled={state.busy || state.changed} onClick={() => void state.act("approve", { digest: approval.approvalDigest, path: approval.path })}>{t("runs.approve")}</Button>
      {run.ai && <Button variant="secondary" disabled={state.busy || state.changed} onClick={() => void state.act("edit", { digest: approval.approvalDigest, path: approval.path })}>{t("common.edit")}</Button>}
    </div>}
    <DecisionDialog open={repeat !== null} title={t("runs.repeat_title")} description={t("runs.repeat_text")} icon="warning" tone="warning" onClose={() => setRepeat(null)} actions={<>
      <Button variant="secondary" onClick={() => setRepeat(null)}>{t("runs.close")}</Button><Button variant="primary" disabled={state.busy} onClick={async () => {
        const result = await state.act("repeat", { triggerKey: repeat, acknowledged: run.id });
        if (result) { setRepeat(null); onRepeated?.(result.id); }
      }}>{t("runs.repeat")}</Button></>} />
  </div>;
}
