import { Modal } from "antd";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { KnowledgeScopeConflict } from "./types";

export function KnowledgeScopeConflictModal({
  conflicts,
  onClose,
  openAgent,
}: {
  conflicts: KnowledgeScopeConflict[];
  onClose: () => void;
  openAgent: (agentId: number) => void;
}) {
  const agents = [...new Map(conflicts.map((conflict) => [conflict.agent.id, conflict.agent])).values()];
  return (
    <Modal className="knowledge-conflict-modal" open title={null} footer={null} closable={false} destroyOnClose>
      <div className="knowledge-conflict-heading">
        <span><Icon name="warning" size={20} /></span>
        <div><h3>Область доступности конфликтует с агентами</h3><p>Операция заблокирована. Ни одно знание не изменено.</p></div>
      </div>
      <div className="knowledge-conflict-list">
        {agents.map((agent) => (
          <div key={agent.id}>
            <span><Icon name="robot" size={17} /></span>
            <strong>{agent.name}</strong>
            <button type="button" onClick={() => openAgent(agent.id)}>Открыть <Icon name="arrow" size={14} /></button>
          </div>
        ))}
      </div>
      <div className="knowledge-conflict-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" onClick={() => agents[0] && openAgent(agents[0].id)}>Перейти к правке агентов</Button>
      </div>
    </Modal>
  );
}
