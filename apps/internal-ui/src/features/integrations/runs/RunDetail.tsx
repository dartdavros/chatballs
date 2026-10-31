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

export function RunDetail({ id, onBack, inChat = false, onRepeated }: { id: string; onBack: () => void; inChat?: boolean; onRepeated?: (id: string) => void }) {
  const state = useRunDetail(id);
  const [repeat, setRepeat] = useState<string | null>(null);
  const run = state.run;
  if (!run) return <div className="run-detail-state">{state.loading ? <LoadingState /> : <EmptyState title={state.error} />}</div>;
  const approval = run.steps.find(step => step.state === "approval");
  return <div className="run-detail">
    <button className="link is-muted has-icon" type="button" onClick={onBack}><Icon name="chevronLeft" size={14} />{t(inChat ? "runs.back_chat" : "runs.back")}</button>
    <header className="run-detail-head"><div><div className="run-title"><h2>{run.name}</h2><RunStatus state={run.state} label={run.stateLabel} /></div>
      <p>{t("runs.run_label", { number: fmt.number(run.number) })} · {fmt.shortDateTime(run.createdAt)}</p></div>
      <div className="run-detail-actions">{run.controls.includes("reconcile") && <Button variant="secondary" disabled={state.busy} onClick={() => void state.act("reconcile")}>{t("runs.reconcile")}</Button>}
        {!run.dataCleared && <Dropdown overlayClassName="app-dropdown" trigger={["click"]} menu={{ items: [
          { key: "cancel", label: t("runs.cancel"), disabled: !run.controls.includes("cancel") },
          { key: "repeat", label: t("runs.repeat"), disabled: !run.controls.includes("repeat") },
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
    <dl className="run-meta"><div><dt>{t("runs.initiator")}</dt><dd>{run.initiator}</dd></div>
      <div><dt>{t("runs.where")}</dt><dd>{run.conversationId ? t("runs.conversation", { number: fmt.number(run.conversationId) }) : "—"}</dd></div>
      <div><dt>{t("runs.started")}</dt><dd>{fmt.shortDateTime(run.createdAt)}</dd></div>
      <div><dt>{t("runs.ended")}</dt><dd>{run.finishedAt ? fmt.shortDateTime(run.finishedAt) : "—"}</dd></div>
      <div><dt>{t("runs.definition_version")}</dt><dd>{run.definitionUpdatedAt ? fmt.shortDateTime(run.definitionUpdatedAt) : "—"}</dd></div>
      <div><dt>{t("runs.connections")}</dt><dd>{run.connection}</dd></div></dl>
    <section className="run-steps"><h3>{t("runs.steps")}</h3>{run.steps.map(step => <div className="run-step" key={step.path}>
      <div className="run-step-title"><strong>{step.title}</strong><RunStatus state={step.state} label={step.stateLabel} /></div>
      {step.error && <p className="run-step-error">{step.error}</p>}
      {!run.dataCleared && <><RunValues schema={step.inputSchema} value={step.arguments} /><RunValues schema={step.outputSchema} value={step.result} /></>}
    </div>)}</section>
    {approval && run.controls.includes("approve") && <Button variant="primary" disabled={state.busy || state.changed} onClick={() => void state.act("approve", { digest: approval.approvalDigest })}>{t("runs.approve")}</Button>}
    <DecisionDialog open={repeat !== null} title={t("runs.repeat_title")} description={t("runs.repeat_text")} icon="warning" tone="warning" onClose={() => setRepeat(null)} actions={<>
      <Button variant="secondary" onClick={() => setRepeat(null)}>{t("runs.close")}</Button><Button variant="primary" disabled={state.busy} onClick={async () => {
        const result = await state.act("repeat", { triggerKey: repeat, acknowledged: run.id });
        if (result) { setRepeat(null); onRepeated?.(result.id); }
      }}>{t("runs.repeat")}</Button></>} />
  </div>;
}
