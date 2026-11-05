import { Dropdown } from "antd";
import { useState } from "react";
import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { groupColorOf } from "../conversations/model";
import { agentTile, agentStatusMeta, createdLabel, openDialogsLine, type AgentCard, type AgentPatch } from "./model";

export function AgentHeader({ card, canManage, busy, apply, toggleAi, onDelete, onTest, testing }: {
  card: AgentCard; canManage: boolean; busy: boolean; testing: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>; toggleAi: () => Promise<void>;
  onDelete: () => void; onTest: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const tile = agentTile(card);
  const status = agentStatusMeta(card);
  const running = card.aiStatus === "ACTIVE";
  // Выключение агента и удаление живут в этом меню, а не отдельными кнопками
  // под карточкой: на странице остаётся один переключатель AI.
  const menuItems = [
    { key: "copy-code", label: <button type="button" onClick={() => { setMenuOpen(false); void navigator.clipboard?.writeText(card.code); }}><Icon name="copy" size={15} />{t("ai.copy_snippet")}</button> },
    { type: "divider" as const },
    {
      key: "active",
      disabled: busy,
      label: (
        <button type="button" onClick={() => { setMenuOpen(false); void apply({ isActive: !card.isActive }); }}>
          <Icon name={card.isActive ? "xCircle" : "check"} size={15} />{card.isActive ? t("ai.turn_agent_off") : t("ai.turn_agent")}
        </button>
      ),
    },
    {
      key: "delete",
      disabled: busy,
      label: (
        <button className="danger" type="button" onClick={() => { setMenuOpen(false); onDelete(); }}>
          <Icon name="trash" size={15} />{t("ai.delete_agent")}</button>
      ),
    },
  ];

  return (
      <header className="agent-head">
        <span className="agent-head-tile" style={{ background: tile.background, color: tile.color }}>
          <Icon name="robot" size={28} strokeWidth={1.8} />
        </span>
        <div className="agent-head-text">
          <div>
            <h2>{card.name}</h2>
            <b className="agents-status" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
          </div>
          <p>
            <span><i style={{ background: card.groupId === null ? "var(--n-5)" : groupColorOf(card.groupId, card.groupColor) }} />{card.groupName ?? t("common.no_group")}</span>
            <i />
            <code>{card.code}</code>
            <i />
            {openDialogsLine(card.counters.openConversations)}
            <i />
            {t("ai.created_on", { date: createdLabel(card.createdAt) })}
          </p>
        </div>
        {canManage && (
          <div className="agent-head-actions">
            <Button variant="secondary" className={`agent-test-button${testing ? " is-active" : ""}`} icon="message" aria-expanded={testing} onClick={onTest}>
              {t("agent_test.open")}
            </Button>
            <Button variant="secondary" className="agent-toggle" icon={running ? "pause" : "bolt"} disabled={busy} onClick={() => void toggleAi()}>
              {running ? t("ai.stop_ai") : t("ai.start_ai")}
            </Button>
            <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown">
              <button className="agent-head-menu" type="button" aria-label={t("ai.agent_actions")} title={t("common.actions")}><Icon name="more" size={17} strokeWidth={2} /></button>
            </Dropdown>
          </div>
        )}
      </header>

  );
}
