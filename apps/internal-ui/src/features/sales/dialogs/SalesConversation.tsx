import { useEffect, useRef, type ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import { channelMeta, statusFor } from "./data";
import type { ApiConversation, ApiMessage } from "./model";
import type { ControlMode, SalesDialog, StatusInfo } from "./types";

function fmtTime(value: string): string {
  return new Date(value).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export function SalesConversation({ controlMode, dialog, detail, onClaim }: { controlMode: ControlMode; dialog: SalesDialog | null; detail: ApiConversation | null; onClaim: () => void }) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const messages = detail?.messages ?? [];
  const lastMessageId = messages.length ? messages[messages.length - 1].id : 0;

  // Скролл к свежим сообщениям при открытии диалога и при новых сообщениях.
  useEffect(() => {
    const node = timelineRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [detail?.id, lastMessageId]);

  if (!dialog) {
    return <div className="sales-timeline"><div className="sales-timeline-inner"><div className="sales-wait-note">Выберите диалог</div></div></div>;
  }
  const status = statusFor(controlMode);
  const channel = channelMeta[dialog.channel];
  return (
    <>
      <div className="sales-conversation-head">
        <div className="sales-conversation-person">
          <span style={{ background: dialog.avatarBg }}>{dialog.initials}</span>
          <div>
            <div><strong>{dialog.name}</strong><StatusBadge status={status} /></div>
            <p>{dialog.product}<i /> <em style={{ background: channel.color }} />{channel.label}</p>
          </div>
        </div>
        <div className="sales-conversation-actions">
          {controlMode === "waiting" && <button className="sales-claim-button" onClick={onClaim}><Icon name="check" size={15} />Забрать</button>}
          {controlMode === "ai" && <button className="sales-ai-button" onClick={onClaim}>Перехватить AI</button>}
          <button className="sales-more-button" aria-label="Действия диалога"><Icon name="more" size={18} /></button>
        </div>
      </div>
      <div className="sales-timeline" ref={timelineRef}>
        <div className="sales-timeline-inner">
          {messages.length === 0 && <div className="sales-wait-note">Пока нет сообщений</div>}
          {messages.map((message) => (
            <MessageRow key={message.id} message={message} dialog={dialog} />
          ))}
        </div>
      </div>
    </>
  );
}

function MessageRow({ message, dialog }: { message: ApiMessage; dialog: SalesDialog }) {
  if (message.author === "SYSTEM") {
    return <div className="sales-event-chip"><Icon name="clock" size={12} />{message.text} · {fmtTime(message.createdAt)}</div>;
  }
  const side = message.author === "CONTACT" ? "client" : message.author === "OPERATOR" ? "operator" : "ai";
  const actor = message.author === "AI" ? "AI-агент" : message.author === "OPERATOR" ? "Оператор" : undefined;
  return (
    <Message side={side} initials={dialog.initials} avatarBg={dialog.avatarBg} actor={actor} time={fmtTime(message.createdAt)}>
      {message.text}
    </Message>
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
