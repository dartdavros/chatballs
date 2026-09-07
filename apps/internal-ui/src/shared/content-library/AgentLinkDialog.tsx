import { Modal } from "antd";
import { useState } from "react";

import { Button } from "../ui-controls";
import { pluralRu } from "../utils";

export type AgentLinkAction = "attach" | "detach";

export type AgentLinkOption = {
  id: number;
  name: string;
  groupName: string | null;
};

export type AgentLinkOutcome = {
  action: AgentLinkAction;
  changed: number;
  skipped: number;
};

function outcomeText(outcome: AgentLinkOutcome, forms: [string, string, string]): string {
  const verb = outcome.action === "attach" ? "Прикреплено" : "Откреплено";
  const main = `${verb}: ${pluralRu(outcome.changed, forms)}.`;
  if (outcome.skipped === 0) return main;
  return `${main} Пропущено: ${outcome.skipped}.`;
}

/**
 * Выбор одного агента для массового прикрепления или открепления статей
 * портала поддержки. У «Базы знаний» после редизайна свой диалог (кадр KB3)
 * с честным списком пропусков.
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
    <Modal className="content-link-modal" open title={title} onCancel={onCancel} footer={null} destroyOnClose>
      <div className="content-dialog-body">
        {outcome ? (
          <p className="content-dialog-outcome">{outcomeText(outcome, forms)}</p>
        ) : (
          <>
            <div className="content-dialog-field">
              <span>Действие</span>
              <div className="content-dialog-segmented">
                <button className={action === "attach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("attach")}>Прикрепить</button>
                <button className={action === "detach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("detach")}>Открепить</button>
              </div>
            </div>
            <label className="content-dialog-field content-dialog-select">
              <span>Агент</span>
              <div>
                <select disabled={busy || agents.length === 0} value={agentId ?? ""} onChange={(event) => setAgentId(event.target.value ? Number(event.target.value) : null)}>
                  <option value="">Выберите агента</option>
                  {agents.map((agent) => (
                    <option value={agent.id} key={agent.id}>
                      {agent.name}{agent.groupName ? ` · ${agent.groupName}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </label>
            {agents.length === 0 && <div className="content-dialog-error">Нет агентов, которым можно прикрепить материалы.</div>}
          </>
        )}
        {error && <div className="content-dialog-error">{error}</div>}
        <div className="content-dialog-actions">
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
