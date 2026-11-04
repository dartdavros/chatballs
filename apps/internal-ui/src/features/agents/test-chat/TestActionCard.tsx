import { useState } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { RunApprovalCard } from "../../integrations/runs/RunApprovalCard";
import { RunDetail } from "../../integrations/runs/RunDetail";
import { RunValues } from "../../integrations/runs/RunValues";
import type { TestAction } from "./model";

export function TestActionCard({ action }: { action: TestAction }) {
  const [details, setDetails] = useState(false);
  if (action.runId) return details ? <RunDetail id={action.runId} inChat onBack={() => setDetails(false)} />
    : <RunApprovalCard id={action.runId} onDetails={() => setDetails(true)} />;
  return <article className="run-feed-card is-ai"><header><Icon name="robot" size={17} /><strong>{action.title}</strong><span className="run-status">{t("agent_actions.not_executed")}</span></header>
    <RunValues schema={action.inputSchema ?? null} value={action.arguments} />
  </article>;
}
