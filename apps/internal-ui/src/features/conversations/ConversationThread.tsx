import { Fragment, useRef } from "react";

import { Icon } from "../../shared/icons";
import { IconButton } from "../../shared/ui-controls";
import { ConversationActions } from "./ConversationActions";
import { ContactAvatar } from "./ContactAvatar";
import { ConversationMessage } from "./ConversationMessage";
import { conversationTimeline } from "./timeline";
import { ToolCallChip } from "../../shared/tool-calls/ToolCallChip";
import { statusFor } from "./data";
import { providerMeta } from "../../shared/providers";
import type { ApiConversation } from "./model";
import type { ConversationHistory } from "./useConversationHistory";
import { useHistoryScroll } from "./useHistoryScroll";
import type { ConversationListItem, ControlMode } from "./types";
import { fmt, t } from "../../i18n";

export function ConversationThread({ controlMode, dialog, detail, history, isOwner = false, onClaim, onRelease, onClose, onSpam, onReturnQueue, canDelete = false, onDelete, onDiagnosticError, onToggleContext, onMobileBack, onExpandList, viewerId = null }: { controlMode: ControlMode; dialog: ConversationListItem | null; detail: ApiConversation | null; history: ConversationHistory; isOwner?: boolean; onClaim: () => void; onRelease: () => void; onClose: () => void; onSpam: () => Promise<boolean>; onReturnQueue: () => void; canDelete?: boolean; onDelete: () => Promise<boolean>; onDiagnosticError: (error: string) => void; onToggleContext?: () => void; onMobileBack?: () => void; onExpandList?: () => void; viewerId?: number | null }) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const messages = history.messages;
  const rows = conversationTimeline(messages);
  // Лента держит низ при новых репликах и догружает предыдущие при подходе к
  // верху, сохраняя место чтения.
  const { onScroll } = useHistoryScroll(timelineRef, {
    conversationId: dialog?.id ?? null,
    messages,
    viewerId,
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
          <ConversationActions open={detail?.lifecycle === "OPEN"} canReturnQueue={controlMode === "human"} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} canDelete={canDelete} onDelete={onDelete} conversationId={dialog.id} canExportDiagnostics={canDelete} onDiagnosticError={onDiagnosticError} />
        </div>
      </div>
      <div className="sales-timeline" ref={timelineRef} onScroll={onScroll}>
        <div className="sales-timeline-inner">
          {history.loaded && messages.length === 0 && <div className="sales-wait-note">{t("conversations.no_messages_yet")}</div>}
          {rows.map(({ message, calls }, index) => (
            <Fragment key={message.id}>
              {(index === 0 || !sameDay(rows[index - 1].message.createdAt, message.createdAt)) && (
                <div className="sales-day-divider"><span />{dayLabel(message.createdAt)}<span /></div>
              )}
              {calls ? <ToolCallChip calls={calls} createdAt={message.createdAt} /> : <ConversationMessage message={message} dialog={dialog} viewerId={viewerId} />}
            </Fragment>
          ))}
        </div>
      </div>
    </>
  );
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
