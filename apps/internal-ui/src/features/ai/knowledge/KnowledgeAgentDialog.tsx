import { Modal } from "antd";
import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Segmented } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { AgentRef } from "../../agents/model";
import type { KnowledgeItem } from "./types";
import { t, tn } from "../../../i18n";

// Прикрепление знаний к агенту (дизайн-базлайн v2, кадр KB3). Один агент за
// операцию: SPEC-CHATBALLS-0029 §6 требует атомарности и журналирования, поэтому
// список пропусков показывается честно, до применения.

type Mode = "attach" | "detach";

const MODES: Array<[Mode, string]> = [["attach", t("common.attach")], ["detach", t("common.detach")]];


type Skip = { item: KnowledgeItem; reason: string };

// Где материал уже стоит, знает сам материал: список agentIds приходит вместе
// со страницей библиотеки, а не собирается по карточкам всех агентов.
function skipsFor(items: KnowledgeItem[], agent: AgentRef | null, mode: Mode): Skip[] {
  if (!agent || agent.aiAgentId === null) return [];
  const agentId = agent.aiAgentId;
  const skips: Skip[] = [];
  items.forEach((item) => {
    const attached = (item.agentIds ?? []).includes(agentId);
    if (mode === "attach") {
      if (attached) skips.push({ item, reason: t("ai.already_attached_agent") });
      else if (!item.isEnabled) skips.push({ item, reason: t("ai.switched_off_replies") });
    } else if (!attached) {
      skips.push({ item, reason: t("ai.not_attached_agent") });
    }
  });
  return skips;
}

function agentMeta(agent: AgentRef): string {
  if (agent.aiStatus !== "ACTIVE") return t("ai.no_ai_knowledge_not_used");
  return t("ai.ai_replies_attached", { count: tn("plural.knowledge", agent.knowledgeCount) });
}

export function KnowledgeAgentDialog({
  agents,
  busy,
  items,
  onCancel,
  onSubmit,
}: {
  agents: AgentRef[];
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
            <h3>{mode === "attach" ? t("ai.attach_agent") : t("ai.detach_from_agent")}</h3>
            <p>{t("ai.selected_one_agent_note", { count: tn("plural.knowledge", items.length) })}</p>
          </div>
          <button aria-label={t("common.close")} className="knowledge-dialog-close" title={t("common.close")} type="button" onClick={onCancel}>
            <Icon name="close" size={15} strokeWidth={2.2} />
          </button>
        </div>
        <Segmented className="knowledge-agent-modes" items={MODES} value={mode} setValue={setMode} />
      </header>

      <div className="knowledge-agent-dialog-body">
        <span className="knowledge-agent-dialog-label">{t("ai.agent")}</span>
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
                <small className="knowledge-agent-tag">{picked ? t("ai.selected") : noAi ? t("ai.no_ai") : t("ai.available")}</small>
              </button>
            );
          })}
          {agents.length === 0 && <p className="knowledge-agent-empty">{t("ai.there_no_agents_yet_create")}</p>}
        </div>
      </div>

      {skips.length > 0 && (
        <div className="knowledge-agent-warning">
          <Icon name="alert" size={16} strokeWidth={2} />
          <span>
            <b>{t("ai.skips_summary", { skipped: skips.length, total: items.length })}</b>{" "}
            {skips.map((skip) => `«${skip.item.title}» ${skip.reason}`).join(", ")}. {t("ai.skips_tail")}
          </span>
        </div>
      )}

      <footer className="knowledge-agent-dialog-foot">
        <span>{t("ai.operation_atomic_if_any_identifier")}<code>ai.manage</code>.
        </span>
        <Button variant="secondary" disabled={busy} onClick={onCancel}>{t("common.cancel")}</Button>
        <Button
          variant="primary"
          disabled={busy || agentId === null || applied === 0}
          onClick={() => agentId !== null && onSubmit(agentId, mode)}
        >
          {mode === "attach" ? t("common.attach") : t("common.detach")} {applied}
        </Button>
      </footer>
    </Modal>
  );
}
