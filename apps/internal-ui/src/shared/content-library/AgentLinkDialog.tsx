import { Modal } from "antd";
import { useState } from "react";

import { Button } from "../ui-controls";
import { t, tn, type MessageKey } from "../../i18n";

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

// Диалог не знает, что именно прикрепляют, — знания или статьи портала, — и
// раньше принимал три формы слова пропсом. Теперь он принимает ключ словаря:
// формы для каждого языка живут в словаре, а не в вызывающем коде.
function outcomeText(outcome: AgentLinkOutcome, countKey: MessageKey): string {
  const verb = outcome.action === "attach" ? t("shared.attached") : t("shared.detached");
  const main = `${verb}: ${tn(countKey, outcome.changed)}.`;
  if (outcome.skipped === 0) return main;
  return `${main} ${t("shared.skipped_count", { count: outcome.skipped })}`;
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
  countKey,
  outcome,
  title,
  onCancel,
  onSubmit,
}: {
  agents: AgentLinkOption[];
  busy: boolean;
  error: string | null;
  countKey: MessageKey;
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
          <p className="content-dialog-outcome">{outcomeText(outcome, countKey)}</p>
        ) : (
          <>
            <div className="content-dialog-field">
              <span>{t("common.action")}</span>
              <div className="content-dialog-segmented">
                <button className={action === "attach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("attach")}>{t("common.attach")}</button>
                <button className={action === "detach" ? "active" : ""} disabled={busy} type="button" onClick={() => setAction("detach")}>{t("common.detach")}</button>
              </div>
            </div>
            <label className="content-dialog-field content-dialog-select">
              <span>{t("common.agent")}</span>
              <div>
                <select disabled={busy || agents.length === 0} value={agentId ?? ""} onChange={(event) => setAgentId(event.target.value ? Number(event.target.value) : null)}>
                  <option value="">{t("shared.pick_agent")}</option>
                  {agents.map((agent) => (
                    <option value={agent.id} key={agent.id}>
                      {agent.name}{agent.groupName ? ` · ${agent.groupName}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            </label>
            {agents.length === 0 && <div className="content-dialog-error">{t("shared.there_no_agents_attach_material")}</div>}
          </>
        )}
        {error && <div className="content-dialog-error">{error}</div>}
        <div className="content-dialog-actions">
          <Button variant="secondary" disabled={busy} onClick={onCancel}>{outcome ? t("common.close") : t("common.cancel")}</Button>
          {!outcome && (
            <Button variant="primary" disabled={busy || agentId === null} onClick={() => agentId !== null && onSubmit(agentId, action)}>{t("profile.apply")}</Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
