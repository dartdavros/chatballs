import { Modal } from "antd";
import { useState } from "react";

import { Button } from "../ui-controls";
import { pluralize } from "./BulkSelectionBar";

export type AgentLinkAction = "attach" | "detach";

export type AgentLinkOption = {
  id: number;
  name: string;
  channelName: string;
  groupName: string | null;
};

export type AgentLinkOutcome = {
  action: AgentLinkAction;
  changed: number;
  skipped: number;
};

function outcomeText(outcome: AgentLinkOutcome, forms: [string, string, string]): string {
  const verb = outcome.action === "attach" ? "Прикреплено" : "Откреплено";
  const main = `${verb}: ${outcome.changed} ${pluralize(outcome.changed, forms)}.`;
  if (outcome.skipped === 0) return main;
  return `${main} Пропущено: ${outcome.skipped}.`;
}

/**
 * Выбор одного агента для массового прикрепления или открепления материалов.
 * Общий для библиотеки знаний и для статей портала поддержки.
 */
export function AgentLinkDialog({
  agents,
  busy,
  error,
  forms,
  outcome,
  title,
  onCancel,
  onSubmit,
}: {
  agents: AgentLinkOption[];
  busy: boolean;
  error: string | null;
  forms: [string, string, string];
  outcome: AgentLinkOutcome | null;
  title: string;
  onCancel: () => void;
  onSubmit: (agentId: number, action: AgentLinkAction) => void;
}) {
  const [agentId, setAgentId] = useState<number | null>(agents[0]?.id ?? null);
  const [action, setAction] = useState<AgentLinkAction>("attach");

  return (
    <Modal className="knowledge-bulk-modal" open title={title} onCancel={onCancel} footer={null} destroyOnClose>
      <div className="knowledge-bulk-dialog-body">
        {outcome ? (
          <p className="knowledge-bulk-outcome">{outcomeText(outcome, forms)}</p>
        ) : (
          <>
            <div className="knowledge-editor-field">
              <span>Действие</span>
              <div className="knowledge-visibility-segmented">
                <button className={action === "attach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("attach")}>Прикрепить</button>
                <button className={action === "detach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("detach")}>Открепить</button>
              </div>
            </div>
            <label className="knowledge-editor-field knowledge-category-select">
              <span>Агент</span>
              <div>
                <select disabled={busy || agents.length === 0} value={agentId ?? ""} onChange={(event) => setAgentId(event.target.value ? Number(event.target.value) : null)}>
                  <option value="">Выберите агента</option>
                  {agents.map((agent) => (
                    <option value={agent.id} key={agent.id}>
                      {agent.name} · {agent.channelName}{agent.groupName ? ` · ${agent.groupName}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </label>
            {agents.length === 0 && <div className="knowledge-editor-error">Нет агентов, которым можно прикрепить материалы.</div>}
          </>
        )}
        {error && <div className="knowledge-editor-error">{error}</div>}
        <div className="knowledge-bulk-dialog-actions">
          <Button variant="secondary" disabled={busy} onClick={onCancel}>{outcome ? "Закрыть" : "Отмена"}</Button>
          {!outcome && (
            <Button variant="primary" disabled={busy || agentId === null} onClick={() => agentId !== null && onSubmit(agentId, action)}>
              Применить
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
