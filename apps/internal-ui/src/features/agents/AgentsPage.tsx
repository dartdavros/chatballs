import { Dropdown, Modal } from "antd";
import { useState } from "react";

import { Icon } from "../../shared/icons";
import { ChannelBadge } from "../../shared/badges";
import { FormField, SelectField } from "../../shared/form-controls";
import { EmptyState, PageHeader, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import { agentStatusLabel, createAgent, setAgentAiActive, type AgentCard } from "./model";

const STATUS_PILL = { active: "active", paused: "draft", disabled: "disabled" } as const;

/** Мастер одного шага (SPEC-HUB-0031 §4.3): имя и необязательная группа. */
function CreateAgentModal({ groups, onClose, onCreated }: { groups: EmployeeGroup[]; onClose: () => void; onCreated: (agentId: number) => void }) {
  const [name, setName] = useState("");
  const [groupId, setGroupId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createAgent({ name: name.trim(), groupId });
      onCreated(created.agent.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось создать агента");
      setSubmitting(false);
    }
  }

  return (
    <Modal open title="Создать агента" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <FormField label="Название" value={name} onChange={setName} placeholder="Например: Приёмная" />
        <SelectField
          label="Группа"
          value={groupId === null ? "" : String(groupId)}
          onChange={(value) => setGroupId(value ? Number(value) : null)}
          options={[["", "Без группы — диалоги видны всем"], ...groups.map((item) => [String(item.id), item.name] as [string, string])]}
        />
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!name.trim() || submitting} onClick={() => void submit()}>
            {submitting ? "Создание…" : "Создать"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function AgentsPage({
  agents,
  groups,
  reload,
  openAgent,
}: {
  agents: AgentCard[];
  groups: EmployeeGroup[];
  reload: () => void;
  openAgent: (agentId: number) => void;
}) {
  const [creating, setCreating] = useState(false);
  const [menuId, setMenuId] = useState<number | null>(null);

  async function toggleAi(card: AgentCard) {
    setMenuId(null);
    await setAgentAiActive(card.id, card.aiStatus !== "ACTIVE").catch(() => undefined);
    reload();
  }

  return (
    <div className="ai-page">
      <PageHeader
        title="Агенты"
        text="Агент отвечает клиентам и собирает диалоги в группу"
        action={<Button variant="primary" icon="plus" onClick={() => setCreating(true)}>Создать агента</Button>}
      />
      {agents.length === 0 ? (
        <EmptyState title="Агент отвечает клиентам первым. Создайте первого" />
      ) : (
        <div className="table-card">
          <table className="baseline-table">
            <thead>
              <tr>
                <th>АГЕНТ</th>
                <th>ГРУППА</th>
                <th>СТАТУС</th>
                <th>ПОДКЛЮЧЕНИЯ</th>
                <th className="numeric">ОТКРЫТЫЕ ДИАЛОГИ</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {agents.map((card) => {
                const status = agentStatusLabel(card);
                const menuItems = [
                  { key: "open", label: <button type="button" onClick={() => { setMenuId(null); openAgent(card.id); }}><Icon name="external" size={15} />Открыть карточку</button> },
                  { type: "divider" as const },
                  {
                    key: "toggle",
                    label: (
                      <button type="button" className={card.aiStatus === "ACTIVE" ? "warning" : ""} onClick={() => void toggleAi(card)}>
                        <Icon name={card.aiStatus === "ACTIVE" ? "pause" : "bolt"} size={15} />
                        {card.aiStatus === "ACTIVE" ? "Остановить AI" : "Запустить AI"}
                      </button>
                    ),
                  },
                ];
                return (
                  <tr key={card.id}>
                    <td>
                      <button className="link is-strong is-neutral" type="button" onClick={() => openAgent(card.id)}>{card.name}</button>
                    </td>
                    <td>{card.groupName ?? <span className="agent-muted">Без группы</span>}</td>
                    <td><StatusPill status={STATUS_PILL[status.tone]} /></td>
                    <td>
                      {card.connections.length === 0 ? (
                        <span className="agent-muted">—</span>
                      ) : (
                        <span style={{ display: "inline-flex", gap: 6 }}>
                          {card.connections.map((connection) => (
                            <ChannelBadge key={connection.id} provider={connection.provider} />
                          ))}
                        </span>
                      )}
                    </td>
                    <td className="numeric">{card.counters.openConversations || <span className="agent-muted">—</span>}</td>
                    <td className="row-actions">
                      <Dropdown
                        menu={{ items: menuItems }}
                        open={menuId === card.id}
                        onOpenChange={(open) => setMenuId(open ? card.id : null)}
                        trigger={["click"]}
                        overlayClassName="app-dropdown"
                      >
                        <button className="row-menu-button" type="button" aria-label="Действия агента"><Icon name="more" /></button>
                      </Dropdown>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {creating && (
        <CreateAgentModal
          groups={groups}
          onClose={() => setCreating(false)}
          onCreated={(agentId) => {
            setCreating(false);
            reload();
            openAgent(agentId);
          }}
        />
      )}
    </div>
  );
}
