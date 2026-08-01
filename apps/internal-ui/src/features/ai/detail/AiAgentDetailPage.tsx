import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { EmptyState, LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { UnderlineTabs } from "../../../shared/ui-controls";
import { AiAgentDetailHeader } from "./AiAgentDetailHeader";
import { AgentEditForm } from "./AgentEditForm";
import { AiAgentInstructionsTab } from "./AiAgentInstructionsTab";
import { AiAgentKnowledgeTab } from "./AiAgentKnowledgeTab";
import { AiAgentMetricsTab } from "./AiAgentMetricsTab";
import { AiAgentOverviewTab } from "./AiAgentOverviewTab";
import { agentTabs, type AgentTab } from "./model";
import { useAiAgentDetail } from "./useAiAgentDetail";

export function AiAgentDetailPage({ agentId, openKnowledge, openChannel, onAgentLoaded, setRoute }: { agentId: number | null; openKnowledge: (knowledgeId: number) => void; openChannel: (channelId: number) => void; onAgentLoaded: (name: string | null) => void; setRoute: (route: RouteKey) => void }) {
  const { agent, loading, error, reload } = useAiAgentDetail(agentId);
  const [tab, setTab] = useState<AgentTab>("overview");
  const [editOpen, setEditOpen] = useState(false);

  useEffect(() => {
    onAgentLoaded(agent?.name ?? null);
    return () => onAgentLoaded(null);
  }, [agent, onAgentLoaded]);

  async function toggleActive() {
    if (!agent) return;
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    reload();
  }

  if (loading) return <div className="ai-page"><LoadingState /></div>;
  if (error || !agent) return <div className="ai-page"><EmptyState title="Не удалось загрузить агента" /></div>;

  return (
    <div className="ai-agent-page">
      <AiAgentDetailHeader agent={agent} onOpenChannel={() => openChannel(agent.channel.id)} />
      <UnderlineTabs className="ai-agent-tabs" items={agentTabs} value={tab} onChange={setTab} />
      {tab === "overview" && <AiAgentOverviewTab agent={agent} toggleActive={toggleActive} onEdit={() => setEditOpen(true)} />}
      {tab === "instructions" && <AiAgentInstructionsTab agent={agent} onChanged={reload} />}
      {tab === "knowledge" && <AiAgentKnowledgeTab agent={agent} openKnowledge={openKnowledge} setRoute={setRoute} />}
      {tab === "metrics" && <AiAgentMetricsTab />}
      {editOpen && <AgentEditForm agent={agent} onClose={() => setEditOpen(false)} onSaved={() => { setEditOpen(false); reload(); }} />}
    </div>
  );
}
