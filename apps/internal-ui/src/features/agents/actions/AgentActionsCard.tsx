import { useState } from "react";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { AgentActionsDialog } from "./AgentActionsDialog";
import { useAgentActions } from "./useAgentActions";
import "./actions.css";

export function AgentActionsCard({ agent }: { agent: number }) {
  const [open, setOpen] = useState(false);
  const state = useAgentActions(agent, true);
  return <section className="agent-card is-side agent-actions-card">
    <h3>{t("agent_actions.title")}</h3><p>{t("agent_actions.description")}</p>
    <Button variant="secondary" onClick={() => setOpen(true)}>{t("agent_actions.configure")}</Button>
    {open && <AgentActionsDialog state={state} onClose={() => setOpen(false)} />}
  </section>;
}
