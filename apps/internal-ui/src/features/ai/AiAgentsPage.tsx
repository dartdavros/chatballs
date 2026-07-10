import { useState } from "react";

import { api } from "../../api/client";
import { PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { AgentsKpiStrip } from "./AgentsKpiStrip";
import { AgentsTable } from "./AgentsTable";
import type { AiAgent } from "./model";

export function AiAgentsPage({ agents, reload, openAgentCreate, openAgent }: { agents: AiAgent[]; reload: () => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void }) {
  const [menuId, setMenuId] = useState<number | null>(null);

  async function toggleActive(agent: AiAgent) {
    const action = agent.isActive ? "deactivate" : "activate";
    await api(`/api/v1/ai/agents/${agent.id}/${action}/`, { method: "POST" }).catch(() => undefined);
    setMenuId(null);
    reload();
  }

  return (
    <div className="ai-page">
      <PageHeader title="AI-агенты" text="Один агент на канал обработки · изменения применяются сразу" action={<Button variant="primary" icon="plus" onClick={() => openAgentCreate(null)}>Создать агента</Button>} />
      <AgentsKpiStrip agents={agents} />
      <AgentsTable agents={agents} menuId={menuId} setMenuId={setMenuId} toggleActive={toggleActive} openAgent={openAgent} />
    </div>
  );
}
