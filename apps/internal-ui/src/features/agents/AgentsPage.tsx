import { useState } from "react";
import { t } from "../../i18n";
import { Pagination } from "../../shared/Pagination";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { usePagedResource } from "../../shared/usePagedResource";
import type { EmployeeGroup } from "../../types";
import { CreateAgentModal } from "./CreateAgentModal";
import { AgentRow } from "./AgentRow";
import { fetchAgentsPage, setAgentAiActive, type AgentCard } from "./model";

export function AgentsPage({
  groups,
  openAgent,
}: {
  groups: EmployeeGroup[];
  openAgent: (agentId: number) => void;
}) {
  const [creating, setCreating] = useState(false);
  // Страницу считает сервер: агентов у крупной организации столько же, сколько
  // точек входа, и отдавать их одним списком нельзя.
  const load = (page: number) => fetchAgentsPage({ group: "all", query: "" }, page);
  const agents = usePagedResource(load, null, t("ai.could_not_load_agents"));

  async function toggleAi(card: AgentCard) {
    await setAgentAiActive(card.id, card.aiStatus !== "ACTIVE").catch(() => undefined);
    void agents.reload();
  }

  return (
    <div className="agents-page">
      <header className="agents-header">
        <div>
          <h2>{t("common.agents")}</h2>
          <p>{t("ai.agent_answers_customers_first_collects")}</p>
        </div>
        <Button variant="primary" className="agents-create" icon="plus" iconSize={15} onClick={() => setCreating(true)}>{t("profile.create_agent")}</Button>
      </header>
      {agents.errorText && <div className="agents-error">{agents.errorText}</div>}
      {agents.total === 0 ? (
        <div className="agents-empty">
          <span><Icon name="robot" size={24} strokeWidth={1.8} /></span>
          <div>
            <strong>{t("ai.agent_answers_customers_first_create")}</strong>
            <p>{t("ai.name_group_all_takes_start")}</p>
          </div>
          <Button variant="primary" className="agents-create is-wide" onClick={() => setCreating(true)}>{t("profile.create_agent")}</Button>
        </div>
      ) : (
        <div className="agents-table">
          <div className="agents-thead">
            <span>{t("common.agent")}</span>
            <span>{t("common.group")}</span>
            <span>{t("common.status")}</span>
            <span>{t("common.model")}</span>
            <span>{t("common.connections")}</span>
            <span className="is-right">{t("ai.open")}</span>
            <span />
          </div>
          {agents.items.map((card) => (
            <AgentRow card={card} openAgent={openAgent} onToggleAi={(item) => void toggleAi(item)} key={card.id} />
          ))}
          {agents.pageCount > 1 && (
            <Pagination
              page={agents.page}
              pageCount={agents.pageCount}
              onPage={agents.setPage}
            />
          )}
        </div>
      )}
      {creating && (
        <CreateAgentModal
          groups={groups}
          onClose={() => setCreating(false)}
          onCreated={(agentId) => {
            setCreating(false);
            void agents.reload();
            openAgent(agentId);
          }}
        />
      )}
    </div>
  );
}
