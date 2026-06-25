import { useEffect, useState } from "react";

import { api } from "../../../api/client";
import { EmptyState } from "../../../shared/ui";
import { UnderlineTabs } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import { AiAgentDetailHeader } from "./AiAgentDetailHeader";
import { AiAgentInstructionsTab } from "./AiAgentInstructionsTab";
import { AiAgentKnowledgeTab } from "./AiAgentKnowledgeTab";
import { AiAgentMetricsTab } from "./AiAgentMetricsTab";
import { AiAgentOverviewTab } from "./AiAgentOverviewTab";
import { AiAgentReleasesTab } from "./AiAgentReleasesTab";
import { agentTabs, type AgentTab } from "./model";
import { useAiAgentDetail } from "./useAiAgentDetail";

export function AiAgentDetailPage({ agentId, setRoute, onAgentLoaded }: { agentId: number | null; setRoute: (route: RouteKey) => void; onAgentLoaded: (name: string | null) => void }) {
  const { agent, releases, knowledge, prompts, loading, error, reload } = useAiAgentDetail(agentId);
  const [tab, setTab] = useState<AgentTab>("overview");

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

  if (loading) return <div className="ai-page"><EmptyState title="Загрузка…" /></div>;
  if (error || !agent) return <div className="ai-page"><EmptyState title="Не удалось загрузить агента" /></div>;

  return (
    <div className="ai-agent-page">
      <AiAgentDetailHeader agent={agent} releases={releases} setRoute={setRoute} />
      <UnderlineTabs className="ai-agent-tabs" items={agentTabs} value={tab} onChange={setTab} />
      {tab === "overview" && <AiAgentOverviewTab agent={agent} toggleActive={toggleActive} />}
      {tab === "instructions" && <AiAgentInstructionsTab prompts={prompts} />}
      {tab === "knowledge" && <AiAgentKnowledgeTab knowledge={knowledge} productName={agent.product.name} />}
      {tab === "releases" && <AiAgentReleasesTab releases={releases} />}
      {tab === "metrics" && <AiAgentMetricsTab />}
    </div>
  );
}
