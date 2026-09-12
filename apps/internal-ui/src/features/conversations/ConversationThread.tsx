import { Fragment, useRef, type ReactNode } from "react";

import { Icon } from "../../shared/icons";
import { IconButton } from "../../shared/ui-controls";
import { ConversationActions } from "./ConversationActions";
import { ContactAvatar } from "./ContactAvatar";
import { EmailMessageBody } from "./EmailMessageBody";
import { FileMessage } from "./FileMessage";
import { VoiceMessage } from "./VoiceMessage";
import { statusFor } from "./data";
import { providerMeta } from "../../shared/providers";
import type { ApiConversation, ApiMessage } from "./model";
import type { ConversationHistory } from "./useConversationHistory";
import { useHistoryScroll } from "./useHistoryScroll";
import type { ConversationListItem, ControlMode, StatusInfo } from "./types";
import { fmt, t } from "../../i18n";

function fmtTime(value: string): string {
  return fmt.time(value);
}

export function ConversationThread({ controlMode, dialog, detail, history, isOwner = false, onClaim, onRelease, onClose, onSpam, onReturnQueue, onArchive, onToggleContext, onMobileBack, onExpandList, viewerId = null }: { controlMode: ControlMode; dialog: ConversationListItem | null; detail: ApiConversation | null; history: ConversationHistory; isOwner?: boolean; onClaim: () => void; onRelease: () => void; onClose: () => void; onSpam: () => Promise<boolean>; onReturnQueue: () => void; onArchive: () => Promise<boolean>; onToggleContext?: () => void; onMobileBack?: () => void; onExpandList?: () => void; viewerId?: number | null }) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const messages = history.messages;
  // Лента держит низ при новых репликах и догружает предыдущие при подходе к
  // верху, сохраняя место чтения.
  const { onScroll } = useHistoryScroll(timelineRef, {
    conversationId: dialog?.id ?? null,
    messages,
    hasOlder: history.hasOlder,
    loadingOlder: history.loadingOlder,
    loadOlder: history.loadOlder,
  });

  if (!dialog) {
    return <div className="sales-timeline"><div className="sales-timeline-inner"><div className="sales-wait-note">{t("conversations.pick_conversation")}</div></div></div>;
  }
  const status = statusFor(controlMode, detail?.assignedOperator?.name);
  const channel = providerMeta[dialog.channel];
  return (
    <>
      <div className="sales-conversation-head">
        {/* Кадр M2: на мобильном лента — отдельный экран, назад к списку. */}
        {onMobileBack && <button className="mobile-back" type="button" aria-label={t("conversations.back_conversation_list")} onClick={onMobileBack}><Icon name="arrow" size={19} /></button>}
        {onExpandList && <IconButton bare icon="collapseLeft" iconSize={17} label={t("conversations.show_list")} className="list-expand" onClick={onExpandList} />}
        <div className="sales-conversation-person">
          <span className="sales-conversation-avatar-wrap">
            <ContactAvatar avatarUrl={dialog.avatarUrl} initials={dialog.initials} background={dialog.avatarBg} className="sales-conversation-avatar" />
            <i style={{ background: status.dot }} />
          </span>
          <div>
            <strong>{dialog.name}</strong>
            {/* Статус · канал · агент (· группа) — одной строкой (кадры A–E). */}
            <p>
              <span className="is-status" style={{ color: status.color }}>{status.label}{dialog.waitLabel ? ` · ${dialog.waitLabel}` : ""}</span>
              <i />
              <span><em style={{ background: channel.color }} />{channel.label}</span>
              <i />
              <span className="is-agent" style={{ color: dialog.agentColor }}><Icon name="robot" size={13} />{dialog.agentName}</span>
              {dialog.groupName && <><i /><span>{dialog.groupName}</span></>}
            </p>
          </div>
        </div>
        <div className="sales-conversation-actions">
          {/* Одно действие взятия (решение 2): очередь и AI — primary; у другого
              сотрудника — вторичная кнопка; «ведёте вы» — «Вернуть AI». */}
          {(controlMode === "waiting" || controlMode === "ai") && (
            <button className="sales-claim-button" onClick={onClaim}><Icon name="check" size={15} />{t("conversations.take_conversation")}</button>
          )}
          {controlMode === "assigned" && <button className="sales-secondary-action" onClick={onClaim}>{t("conversations.take_conversation")}</button>}
          {controlMode === "human" && <button className="sales-secondary-action" onClick={onRelease}>{t("conversations.hand_back_ai")}</button>}
          {/* Кадр S2: на узком экране контекст-панель — выдвижная, кнопка в шапке. */}
          {onToggleContext && <IconButton icon="user" label={t("conversations.conversation_context")} className="ctx-toggle" onClick={onToggleContext} />}
          <ConversationActions open={detail?.lifecycle === "OPEN"} canReturnQueue={controlMode === "human"} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} onArchive={onArchive} />
        </div>
      </div>
      <div className="sales-timeline" ref={timelineRef} onScroll={onScroll}>
        <div className="sales-timeline-inner">
          {history.loaded && messages.length === 0 && <div className="sales-wait-note">{t("conversations.no_messages_yet")}</div>}
          {messages.map((message, index) => (
            <Fragment key={message.id}>
              {(index === 0 || !sameDay(messages[index - 1].createdAt, message.createdAt)) && (
                <div className="sales-day-divider"><span />{dayLabel(message.createdAt)}<span /></div>
              )}
              <MessageRow message={message} dialog={dialog} viewerId={viewerId} />
            </Fragment>
          ))}
        </div>
      </div>
    </>
  );
}

function MessageRow({ message, dialog, viewerId }: { message: ApiMessage; dialog: ConversationListItem; viewerId: number | null }) {
  if (message.author === "SYSTEM") {
    // Системное событие (кадры B, C): передача — предупреждение, взятие и
    // возврат — акцент. Тон выбирается по коду события, а не по словам в
    // тексте: текст приходит на языке читателя и на английском не совпал бы
    // ни с одной русской регуляркой.
    const tone = message.systemEvent === "ai_handed_over" || message.systemEvent === "ai_unavailable"
      ? "warning"
      : message.systemEvent === "operator_took" || message.systemEvent === "returned_to_ai" || message.systemEvent === "returned_to_queue"
        ? "claimed"
        : "";
    return <div className={`sales-event-chip ${tone}`}><Icon name="clock" size={12} />{message.text}<span>·</span>{fmtTime(message.createdAt)}</div>;
  }
  const side = message.author === "CONTACT" ? "client" : message.author === "OPERATOR" ? "operator" : "ai";
  // Подпись исходящего (решение 4a): «AI · Консультант», «Анна Ким», «Елена Кузнецова · вы».
  const actor = message.author === "AI"
    ? `AI · ${dialog.agentName}`
    : message.author === "OPERATOR"
      ? `${message.authorName || t("common.operator")}${viewerId != null && message.authorUserId === viewerId ? t("common.you_suffix") : ""}`
      : undefined;
  return (
    <Message side={side} actor={actor} actorColor={message.author === "AI" ? dialog.agentColor : undefined} time={fmtTime(message.createdAt)} authorInitials={message.authorName ? initialsOf(message.authorName) : ""} authorAvatarUrl={message.authorAvatarUrl ?? null}>
      {message.kind === "voice"
        ? <VoiceMessage message={message} />
        : message.kind === "file"
          ? <FileMessage message={message} />
        : message.author === "CONTACT" && dialog.channel === "EMAIL"
          ? <EmailMessageBody html={message.contentHtml} text={message.text} />
          : message.text}
    </Message>
  );
}

function StatusBadge({ status }: { status: StatusInfo }) {
  return <span className="sales-status-badge" style={{ background: status.bg, borderColor: status.border, color: status.color }}><i style={{ background: status.dot }} />{status.label}</span>;
}

// Сообщения (решение 4a): у клиента аватара нет — он в шапке; исходящие справа
// с аватаром AI/сотрудника, подписью и отметкой доставки.
function Message({ side, actor, actorColor, authorInitials, authorAvatarUrl, time, children }: { side: "ai" | "client" | "operator"; actor?: string; actorColor?: string; authorInitials?: string; authorAvatarUrl?: string | null; time: string; children: ReactNode }) {
  return (
    <div className={`sales-message ${side}`}>
      {side !== "client" && (
        <div className="sales-message-avatar" style={side === "ai" && actorColor ? { color: actorColor, background: `color-mix(in srgb, ${actorColor} 14%, var(--surface-card))`, borderColor: `color-mix(in srgb, ${actorColor} 30%, var(--surface-card))` } : undefined}>
          {side === "ai" ? <Icon name="robot" size={16} /> : authorAvatarUrl ? <img src={authorAvatarUrl} alt="" /> : <span>{authorInitials}</span>}
        </div>
      )}
      <div className="sales-message-content">
        {actor && <strong style={actorColor ? { color: actorColor } : undefined}>{actor}</strong>}
        <div>{children}</div>
        <small>{time}{side !== "client" && <Icon name="check" size={13} />}</small>
      </div>
    </div>
  );
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

function sameDay(a: string, b: string): boolean {
  return new Date(a).toDateString() === new Date(b).toDateString();
}

// Разделитель дней в ленте (кадр A): «Сегодня», «Вчера», дата.
function dayLabel(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) return t("common.today");
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return t("admin.yesterday");
  return fmt.dayMonthLong(date);
}
