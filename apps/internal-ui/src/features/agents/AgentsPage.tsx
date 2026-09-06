import { Dropdown, Modal } from "antd";
import { useState } from "react";

import { ChannelGlyph } from "../../shared/badges";
import { FormField, SelectField } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import { groupColorOf } from "../conversations/model";
import {
  agentModelLabel,
  agentStatusMeta,
  agentTile,
  agentTint,
  createAgent,
  setAgentAiActive,
  type AgentCard,
} from "./model";

// Список агентов (дизайн-базлайн v2, «Агенты Baseline», кадры G1, G2, S1):
// агент · группа · статус · модель · подключения · открытые · ⋯.

/** Мастер одного шага (SPEC-HUB-0031 §4.3, кадр G2): имя и группа. */
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
    <Modal className="agent-create-modal" open width={440} title="Создать агента" onCancel={onClose} footer={null} destroyOnClose>
      <p className="agent-create-lead">Один шаг. Инструкции, модель, знания и подключения — потом, на карточке агента.</p>
      <div className="agent-create-fields">
        <FormField label="Название" value={name} onChange={setName} placeholder="Например: Приёмная" />
        <SelectField
          label="Группа"
          value={groupId === null ? "" : String(groupId)}
          onChange={(value) => setGroupId(value ? Number(value) : null)}
          options={[["", "Без группы — диалоги видны всем"], ...groups.map((item) => [String(item.id), item.name] as [string, string])]}
        />
        {error && <div className="agent-form-error">{error}</div>}
      </div>
      <div className="agent-create-actions">
        <Button variant="secondary" onClick={onClose}>Отмена</Button>
        <Button variant="primary" disabled={!name.trim() || submitting} onClick={() => void submit()}>
          {submitting ? "Создание…" : "Создать"}
        </Button>
      </div>
    </Modal>
  );
}

/** Строка списка (кадр G1). Вся строка открывает карточку. */
function AgentRow({ card, openAgent, onToggleAi }: { card: AgentCard; openAgent: (agentId: number) => void; onToggleAi: (card: AgentCard) => void }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const tile = agentTile(card);
  const status = agentStatusMeta(card);
  const open = card.counters.openConversations;
  const menuItems = [
    { key: "open", label: <button type="button" onClick={() => { setMenuOpen(false); openAgent(card.id); }}><Icon name="external" size={15} />Открыть карточку</button> },
    { type: "divider" as const },
    {
      key: "toggle",
      label: (
        <button type="button" className={card.aiStatus === "ACTIVE" ? "warning" : ""} onClick={() => { setMenuOpen(false); onToggleAi(card); }}>
          <Icon name={card.aiStatus === "ACTIVE" ? "pause" : "bolt"} size={15} />
          {card.aiStatus === "ACTIVE" ? "Остановить AI" : "Запустить AI"}
        </button>
      ),
    },
  ];

  return (
    <div className={`agents-row ${card.isActive ? "" : "is-off"}`} role="button" tabIndex={0} onClick={() => openAgent(card.id)} onKeyDown={(event) => { if (event.key === "Enter") openAgent(card.id); }}>
      <div className="agents-row-agent">
        <span className="agents-tile" style={{ background: tile.background, color: tile.color }}>
          <Icon name="robot" size={20} strokeWidth={1.9} />
        </span>
        <span>
          <strong>{card.name}</strong>
          <small>{card.code}</small>
        </span>
      </div>
      <span className={`agents-row-group ${card.groupId === null ? "is-none" : ""}`}>
        {card.groupId !== null && <i style={{ background: groupColorOf(card.groupId, card.groupColor) }} />}
        {card.groupName ?? "Без группы"}
      </span>
      <b className="agents-status" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
      <span className="agents-row-model">{agentModelLabel(card)}</span>
      <div className="agents-row-conns">
        {card.connections.length === 0
          ? <span className="agents-row-dash">—</span>
          : card.connections.map((connection) => {
            const tint = agentTint(connection.provider);
            return (
              <span className="agents-conn-tile" style={{ background: tint.bg, color: tint.color }} title={tint.full} key={connection.id}>
                <ChannelGlyph provider={connection.provider} size={14} />
                {connection.status === "ERROR" && <i />}
              </span>
            );
          })}
      </div>
      <div className="agents-row-open" style={{ color: open ? "var(--warning-text)" : "var(--n-5)" }}>{open || "—"}</div>
      <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown">
        <button className="agents-row-menu" type="button" aria-label="Действия агента" title="Действия" onClick={(event) => event.stopPropagation()}><Icon name="more" size={16} strokeWidth={2} /></button>
      </Dropdown>
    </div>
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

  async function toggleAi(card: AgentCard) {
    await setAgentAiActive(card.id, card.aiStatus !== "ACTIVE").catch(() => undefined);
    reload();
  }

  return (
    <div className="agents-page">
      <header className="agents-header">
        <div>
          <h2>Агенты</h2>
          <p>Агент отвечает клиентам первым и собирает диалоги в группу</p>
        </div>
        <Button variant="primary" className="agents-create" icon="plus" iconSize={15} onClick={() => setCreating(true)}>Создать агента</Button>
      </header>
      {agents.length === 0 ? (
        <div className="agents-empty">
          <span><Icon name="robot" size={24} strokeWidth={1.8} /></span>
          <div>
            <strong>Агент отвечает клиентам первым. Создайте первого</strong>
            <p>Имя и группа — всё, что нужно для старта. Инструкции, знания и подключения настраиваются потом на карточке.</p>
          </div>
          <Button variant="primary" className="agents-create is-wide" onClick={() => setCreating(true)}>Создать агента</Button>
        </div>
      ) : (
        <div className="agents-table">
          <div className="agents-thead">
            <span>Агент</span>
            <span>Группа</span>
            <span>Статус</span>
            <span>Модель</span>
            <span>Подключения</span>
            <span className="is-right">Открытые</span>
            <span />
          </div>
          {agents.map((card) => (
            <AgentRow card={card} openAgent={openAgent} onToggleAi={(item) => void toggleAi(item)} key={card.id} />
          ))}
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
