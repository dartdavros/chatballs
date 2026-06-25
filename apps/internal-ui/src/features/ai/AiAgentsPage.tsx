import { useState } from "react";

import { api } from "../../api/client";
import type { RouteKey } from "../../types";
import { EmptyState, PageHeader } from "../../shared/ui";
import { AgentsKpiStrip } from "./AgentsKpiStrip";
import { AgentsTable } from "./AgentsTable";
import type { AiAgent, AiRelease } from "./model";
import { useAiAgents } from "./useAiAgents";

export function AiAgentsPage({ setRoute, openAgent, openRelease }: { setRoute: (route: RouteKey) => void; openAgent: (agentId: number) => void; openRelease: (releaseId: number) => void }) {
  const { agents, releases, loading, error, reload } = useAiAgents();
  const [menuId, setMenuId] = useState<number | null>(null);

  async function toggleActive(agent: AiAgent) {
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    setMenuId(null);
    reload();
  }

  async function createRelease(agent: AiAgent) {
    try {
      const { release } = await api<{ release: AiRelease }>("/api/v1/ai/releases/", { method: "POST", body: JSON.stringify({ product: agent.product.code }) });
      setMenuId(null);
      reload();
      openRelease(release.id);
    } catch {
      setMenuId(null);
    }
  }

  return (
    <div className="ai-page">
      <PageHeader title="AI-агенты" text="Sales-агенты продуктов · один агент на продукт" />
      {loading ? (
        <EmptyState title="Загрузка…" />
      ) : error ? (
        <EmptyState title="Не удалось загрузить агентов" />
      ) : (
        <>
          <AgentsKpiStrip agents={agents} />
          <AgentsTable agents={agents} releases={releases} menuId={menuId} setMenuId={setMenuId} toggleActive={toggleActive} createRelease={createRelease} setRoute={setRoute} openAgent={openAgent} openRelease={openRelease} />
        </>
      )}
    </div>
  );
}
