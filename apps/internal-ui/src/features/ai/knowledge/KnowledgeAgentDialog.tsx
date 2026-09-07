import { Modal } from "antd";
import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Segmented } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { pluralRu } from "../../../shared/utils";
import type { AgentCard } from "../../agents/model";
import type { KnowledgeItem } from "./types";

// Прикрепление знаний к агенту (дизайн-базлайн v2, кадр KB3). Один агент за
// операцию: SPEC-HUB-0029 §6 требует атомарности и журналирования, поэтому
// список пропусков показывается честно, до применения.

type Mode = "attach" | "detach";

const MODES: Array<[Mode, string]> = [["attach", "Прикрепить"], ["detach", "Открепить"]];

const KNOWLEDGE_FORMS: [string, string, string] = ["знание", "знания", "знаний"];

type Skip = { item: KnowledgeItem; reason: string };

function skipsFor(items: KnowledgeItem[], agent: AgentCard | null, mode: Mode): Skip[] {
  if (!agent) return [];
  const attached = new Set(agent.knowledge.map((item) => item.id));
  const skips: Skip[] = [];
  items.forEach((item) => {
    if (mode === "attach") {
      if (attached.has(item.id)) skips.push({ item, reason: "уже прикреплён к этому агенту" });
      else if (!item.isEnabled) skips.push({ item, reason: "выключен в ответах" });
    } else if (!attached.has(item.id)) {
      skips.push({ item, reason: "не прикреплён к этому агенту" });
    }
  });
  return skips;
}

function agentMeta(agent: AgentCard): string {
  if (agent.aiStatus !== "ACTIVE") return "Без AI — знания не используются";
  return `AI отвечает · ${pluralRu(agent.knowledge.length, KNOWLEDGE_FORMS)} прикреплено`;
}

export function KnowledgeAgentDialog({
  agents,
  busy,
  items,
  onCancel,
  onSubmit,
}: {
  agents: AgentCard[];
  busy: boolean;
  items: KnowledgeItem[];
  onCancel: () => void;
  onSubmit: (agentId: number, mode: Mode) => void;
}) {
  const [mode, setMode] = useState<Mode>("attach");
  const [agentId, setAgentId] = useState<number | null>(agents[0]?.aiAgentId ?? null);
  const agent = agents.find((item) => item.aiAgentId === agentId) ?? null;
  const skips = skipsFor(items, agent, mode);
  const applied = items.length - skips.length;

  return (
    <Modal className="knowledge-agent-dialog" open width={560} title={null} footer={null} closable={false} onCancel={onCancel} destroyOnHidden>
      <header className="knowledge-agent-dialog-head">
        <div className="knowledge-agent-dialog-title">
          <div>
            <h3>{mode === "attach" ? "Прикрепить к агенту" : "Открепить от агента"}</h3>
            <p>Выбрано {pluralRu(items.length, KNOWLEDGE_FORMS)}. Один агент за операцию — так видно, что именно изменилось.</p>
          </div>
          <button aria-label="Закрыть" className="knowledge-dialog-close" title="Закрыть" type="button" onClick={onCancel}>
            <Icon name="close" size={15} strokeWidth={2.2} />
          </button>
        </div>
        <Segmented className="knowledge-agent-modes" items={MODES} value={mode} setValue={setMode} />
      </header>

      <div className="knowledge-agent-dialog-body">
        <span className="knowledge-agent-dialog-label">АГЕНТ</span>
        <div className="knowledge-agent-picks">
          {agents.map((item) => {
            const picked = item.aiAgentId === agentId;
            const noAi = item.aiStatus !== "ACTIVE";
            return (
              <button
                className={`knowledge-agent-pick${picked ? " is-picked" : ""}${noAi ? " is-muted" : ""}`}
                key={item.aiAgentId}
                type="button"
                onClick={() => setAgentId(item.aiAgentId)}
              >
                <i className="knowledge-agent-radio"><b /></i>
                <span>
                  <strong>{item.name}</strong>
                  <small>{agentMeta(item)}</small>
                </span>
                <small className="knowledge-agent-tag">{picked ? "выбран" : noAi ? "без AI" : "доступен"}</small>
              </button>
            );
          })}
          {agents.length === 0 && <p className="knowledge-agent-empty">Агентов пока нет — создайте агента, чтобы прикреплять к нему знания.</p>}
        </div>
      </div>

      {skips.length > 0 && (
        <div className="knowledge-agent-warning">
          <Icon name="alert" size={16} strokeWidth={2} />
          <span>
            <b>{skips.length} из {items.length} будут пропущены:</b>{" "}
            {skips.map((skip) => `«${skip.item.title}» ${skip.reason}`).join(", ")}. Состав знаний
            агента по ним не изменится.
          </span>
        </div>
      )}

      <footer className="knowledge-agent-dialog-foot">
        <span>
          Операция атомарна: при недоступном идентификаторе не меняется ничего. Требуется право <code>ai.manage</code>.
        </span>
        <Button variant="secondary" disabled={busy} onClick={onCancel}>Отмена</Button>
        <Button
          variant="primary"
          disabled={busy || agentId === null || applied === 0}
          onClick={() => agentId !== null && onSubmit(agentId, mode)}
        >
          {mode === "attach" ? "Прикрепить" : "Открепить"} {applied}
        </Button>
      </footer>
    </Modal>
  );
}
