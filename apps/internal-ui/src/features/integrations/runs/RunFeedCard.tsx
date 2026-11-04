import { fmt, t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { RunStatus } from "./RunStatus";
import { useConversationRuns } from "./conversationContext";
import type { RunSummary } from "./types";
import { RunApprovalCard } from "./RunApprovalCard";

export function RunFeedCard({ run }: { run: RunSummary }) {
  const state = useConversationRuns();
  if (run.ai && run.state === "approval") return <RunApprovalCard id={run.id} onDetails={() => state?.openRun(run.id)} />;
  return <article className="run-feed-card"><header><Icon name={run.ai ? "robot" : "plug"} size={17} /><strong>{run.name}</strong><RunStatus state={run.state} label={run.stateLabel} /></header>
    <small>{t("runs.run_label", { number: fmt.number(run.number) })} · {run.initiator}</small>
    {run.progress.map((step, index) => <div className="run-feed-step" key={index}><Icon name={step.state === "completed" ? "check" : step.state === "failed" ? "close" : "clock"} size={13} /><span>{step.title}</span><small>{step.stateLabel}</small></div>)}
    {run.state === "unknown" && <p>{t("runs.unknown_text")}</p>}
    <footer><button type="button" className="link" onClick={() => state?.openRun(run.id)}>{t("runs.details")}</button><time>{fmt.time(run.createdAt)}</time></footer>
  </article>;
}
