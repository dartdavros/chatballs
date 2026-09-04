import { useEffect, useRef, type ReactNode } from "react";

import { Icon } from "../../shared/icons";
import { IconButton } from "../../shared/ui-controls";
import { ConversationActions } from "./ConversationActions";
import { ContactAvatar } from "./ContactAvatar";
import { EmailMessageBody } from "./EmailMessageBody";
import { VoiceMessage } from "./VoiceMessage";
import { statusFor } from "./data";
import { providerMeta } from "../../shared/providers";
import type { ApiConversation, ApiMessage } from "./model";
import type { ConversationListItem, ControlMode, StatusInfo } from "./types";

function fmtTime(value: string): string {
  return new Date(value).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

export function ConversationThread({ controlMode, dialog, detail, isOwner = false, onClaim, onCall, onClose, onSpam, onReturnQueue, onArchive, onToggleContext, onMobileBack }: { controlMode: ControlMode; dialog: ConversationListItem | null; detail: ApiConversation | null; isOwner?: boolean; onClaim: () => void; onCall: (kind: "AUDIO" | "VIDEO") => void; onClose: () => void; onSpam: () => Promise<boolean>; onReturnQueue: () => void; onArchive: () => Promise<boolean>; onToggleContext?: () => void; onMobileBack?: () => void }) {
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
  const status = statusFor(controlMode, detail?.assignedOperator?.name);
  const channel = providerMeta[dialog.channel];
  return (
    <>
      <div className="sales-conversation-head">
        {/* Кадр M2: на мобильном лента — отдельный экран, назад к списку. */}
        {onMobileBack && <button className="mobile-back" type="button" aria-label="К списку диалогов" onClick={onMobileBack}><Icon name="arrow" size={19} /></button>}
        <div className="sales-conversation-person">
          <ContactAvatar avatarUrl={dialog.avatarUrl} initials={dialog.initials} background={dialog.avatarBg} className="sales-conversation-avatar" />
          <div>
            <div><strong>{dialog.name}</strong><StatusBadge status={status} /></div>
            <p>{dialog.product}<i /> <em style={{ background: channel.color }} />{channel.label}</p>
          </div>
        </div>
        <div className="sales-conversation-actions">
          {/* Владелец может перехватить любой открытый диалог (в т.ч. у другого оператора);
              обычный сотрудник — только забрать из очереди или перехватить у AI. */}
          {isOwner && detail?.lifecycle === "OPEN" && !detail?.isAssignedToViewer && (
            <button className="sales-ai-button" onClick={onClaim}>Перехватить диалог</button>
          )}
          {!isOwner && controlMode === "waiting" && <button className="sales-claim-button" onClick={onClaim}><Icon name="check" size={15} />Забрать</button>}
          {!isOwner && controlMode === "ai" && <button className="sales-ai-button" onClick={onClaim}>Перехватить AI</button>}
          {detail?.lifecycle === "OPEN" && dialog.channel !== "EMAIL" && (
            <>
              <IconButton icon="phone" label="Запросить аудиозвонок" className="is-audio" onClick={() => onCall("AUDIO")} />
              <IconButton icon="video" label="Запросить видеозвонок" className="is-video" onClick={() => onCall("VIDEO")} />
            </>
          )}
          {/* Кадр S2: на узком экране контекст-панель — выдвижная, кнопка в шапке. */}
          {onToggleContext && <IconButton icon="user" label="Контекст диалога" className="ctx-toggle" onClick={onToggleContext} />}
          <ConversationActions open={detail?.lifecycle === "OPEN"} canReturnQueue={controlMode === "human"} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} onArchive={onArchive} />
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

function MessageRow({ message, dialog }: { message: ApiMessage; dialog: ConversationListItem }) {
  if (message.author === "SYSTEM") {
    return <div className="sales-event-chip"><Icon name="clock" size={12} />{message.text} · {fmtTime(message.createdAt)}</div>;
  }
  const side = message.author === "CONTACT" ? "client" : message.author === "OPERATOR" ? "operator" : "ai";
  const actor = message.author === "AI" ? "AI-агент" : message.author === "OPERATOR" ? "Оператор" : undefined;
  return (
    <Message side={side} initials={dialog.initials} avatarBg={dialog.avatarBg} avatarUrl={dialog.avatarUrl} actor={actor} time={fmtTime(message.createdAt)}>
      {message.kind === "voice"
        ? <VoiceMessage message={message} />
        : message.author === "CONTACT" && dialog.channel === "EMAIL"
          ? <EmailMessageBody html={message.contentHtml} text={message.text} />
          : message.text}
    </Message>
  );
}

function StatusBadge({ status }: { status: StatusInfo }) {
  return <span className="sales-status-badge" style={{ background: status.bg, borderColor: status.border, color: status.color }}><i style={{ background: status.dot }} />{status.label}</span>;
}

function Message({ side, initials, avatarBg, avatarUrl, actor, time, children }: { side: "ai" | "client" | "operator"; initials?: string; avatarBg?: string; avatarUrl?: string; actor?: string; time: string; children: ReactNode }) {
  return (
    <div className={`sales-message ${side}`}>
      <div className="sales-message-avatar">{side === "ai" ? <Icon name="robot" size={16} /> : <ContactAvatar avatarUrl={avatarUrl} initials={initials ?? ""} background={avatarBg ?? "#8c8c8c"} className="sales-message-avatar-img" />}</div>
      <div className="sales-message-content">
        {actor && <strong>{actor}</strong>}
        <div>{children}</div>
        <small>{time}</small>
      </div>
    </div>
  );
}
