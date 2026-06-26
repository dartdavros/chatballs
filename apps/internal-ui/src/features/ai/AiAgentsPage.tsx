import { useState } from "react";

import { api } from "../../api/client";
import type { RouteKey } from "../../types";
import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { AgentsKpiStrip } from "./AgentsKpiStrip";
import { AgentsTable } from "./AgentsTable";
import type { AiAgent } from "./model";
import { useAiAgents } from "./useAiAgents";

export function AiAgentsPage({ setRoute, openAgentCreate, openAgent, openRelease }: { setRoute: (route: RouteKey) => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void; openRelease: (releaseId: number) => void }) {
  const { agents, releases, loading, error, reload } = useAiAgents();
  const [menuId, setMenuId] = useState<number | null>(null);

  async function toggleActive(agent: AiAgent) {
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    setMenuId(null);
    reload();
  }

  return (
    <div className="ai-page">
      <PageHeader title="AI-агенты" text="Sales-агенты продуктов · один агент на продукт" action={<Button variant="primary" icon="plus" onClick={() => openAgentCreate(null)}>Создать агента</Button>} />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <EmptyState title="Не удалось загрузить агентов" />
      ) : (
        <>
          <AgentsKpiStrip agents={agents} />
          <AgentsTable agents={agents} releases={releases} menuId={menuId} setMenuId={setMenuId} toggleActive={toggleActive} setRoute={setRoute} openAgent={openAgent} openRelease={openRelease} />
        </>
      )}
    </div>
  );
}
