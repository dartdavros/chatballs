import { useState } from "react";

import { api } from "../../api/client";
import type { RouteKey } from "../../types";
import { EmptyState, PageHeader } from "../../shared/ui";
import { AgentsKpiStrip } from "./AgentsKpiStrip";
import { AgentsTable } from "./AgentsTable";
import { AiSubnav } from "./AiSubnav";
import type { AiAgent } from "./model";
import { useAiAgents } from "./useAiAgents";

export function AiAgentsPage({ route, setRoute }: { route: RouteKey; setRoute: (route: RouteKey) => void }) {
  const { agents, releases, loading, error, reload } = useAiAgents();
  const [menuId, setMenuId] = useState<number | null>(null);

  async function toggleActive(agent: AiAgent) {
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    setMenuId(null);
    reload();
  }

  return (
    <>
      <AiSubnav route={route} setRoute={setRoute} />
      <div className="ai-page">
        <PageHeader title="AI-агенты" text="Sales-агенты продуктов · один агент на продукт" />
        {loading ? (
          <EmptyState title="Загрузка…" />
        ) : error ? (
          <EmptyState title="Не удалось загрузить агентов" />
        ) : (
          <>
            <AgentsKpiStrip agents={agents} />
            <AgentsTable agents={agents} releases={releases} menuId={menuId} setMenuId={setMenuId} toggleActive={toggleActive} />
          </>
        )}
      </div>
    </>
  );
}
