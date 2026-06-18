import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import { channelMeta, statusFor } from "./data";
import type { ControlMode, SalesDialog, StatusInfo } from "./types";

export function SalesConversation({ controlMode, selected, setControlMode }: { controlMode: ControlMode; selected: SalesDialog; setControlMode: (mode: ControlMode) => void }) {
  const status = statusFor(controlMode);
  const channel = channelMeta[selected.channel];
  return (
    <>
      <div className="sales-conversation-head">
        <div className="sales-conversation-person">
          <span style={{ background: selected.avatarBg }}>{selected.initials}</span>
          <div>
            <div><strong>{selected.name}</strong><StatusBadge status={status} /></div>
            <p>{selected.product}<i /> <em style={{ background: channel.color }} />{channel.label}<i />{channel.handle}</p>
          </div>
        </div>
        <div className="sales-conversation-actions">
          {controlMode === "waiting" && <button className="sales-claim-button" onClick={() => setControlMode("human")}><Icon name="check" size={15} />Забрать</button>}
          {controlMode === "ai" && <button className="sales-ai-button" onClick={() => setControlMode("human")}>Перехватить AI</button>}
          <button className="sales-more-button" aria-label="Действия диалога"><Icon name="more" size={18} /></button>
        </div>
      </div>
      <div className="sales-timeline">
        <div className="sales-timeline-inner">
          <div className="sales-day-divider"><span />Сегодня<span /></div>
          <div className="sales-event-chip"><Icon name="clock" size={12} />Диалог начат · канал MAX · 14:02</div>
          <Message side="client" initials="МС" avatarBg="#eb6f4b" time="14:02">Здравствуйте! Смотрю FirePage для лендингов. Есть тариф на команду?</Message>
          <Message side="ai" actor="AI-агент FirePage" time="14:03">Да! Для команд есть тариф <b>Business</b>: до 10 пользователей, общие проекты и приоритетная поддержка. Помесячная оплата доступна.</Message>
          <Message side="client" initials="МС" avatarBg="#eb6f4b" time="14:06">А интеграция с amoCRM есть? Лучше бы поговорить с менеджером.</Message>
          <div className="sales-event-chip warning"><Icon name="team" size={12} />AI передал диалог оператору · причина: запрос человека (CRM-интеграция)</div>
          {controlMode === "waiting" && <div className="sales-wait-note">Ожидает оператора · 4 мин</div>}
          {controlMode === "ai" && <TypingMessage />}
          {controlMode === "human" && <div className="sales-event-chip claimed"><Icon name="check" size={13} />Иван Петров забрал диалог · 14:09</div>}
          {controlMode === "human" && <Message side="operator" initials="ИП" avatarBg="#1677ff" actor="Иван · оператор" time="14:10">Здравствуйте, Мария! Я подключился. По amoCRM — у FirePage Business есть готовая двусторонняя интеграция, лиды и сделки синхронизируются автоматически. Расскажу подробнее?</Message>}
        </div>
      </div>
    </>
  );
}

function StatusBadge({ status }: { status: StatusInfo }) {
  return <span className="sales-status-badge" style={{ background: status.bg, borderColor: status.border, color: status.color }}><i style={{ background: status.dot }} />{status.label}</span>;
}

function Message({ side, initials, avatarBg, actor, time, children }: { side: "ai" | "client" | "operator"; initials?: string; avatarBg?: string; actor?: string; time: string; children: ReactNode }) {
  return (
    <div className={`sales-message ${side}`}>
      <div className="sales-message-avatar">{side === "ai" ? <Icon name="robot" size={16} /> : <span style={{ background: avatarBg }}>{initials}</span>}</div>
      <div className="sales-message-content">
        {actor && <strong>{actor}</strong>}
        <div>{children}</div>
        <small>{time}</small>
      </div>
    </div>
  );
}

function TypingMessage() {
  return (
    <div className="sales-message ai typing">
      <div className="sales-message-avatar"><Icon name="robot" size={16} /></div>
      <div className="sales-typing-bubble"><span /><span /><span /></div>
    </div>
  );
}
