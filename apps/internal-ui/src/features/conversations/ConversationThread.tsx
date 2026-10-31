import { Fragment, useMemo, useRef } from "react";

import { Icon } from "../../shared/icons";
import { IconButton } from "../../shared/ui-controls";
import { ConversationActions } from "./ConversationActions";
import { TransferAction } from "../transfers/TransferAction";
import { useConversationTransfer } from "../transfers/useConversationTransfer";
import { ContactAvatar } from "./ContactAvatar";
import { ConversationComment } from "./ConversationComment";
import { ConversationMessage } from "./ConversationMessage";
import { isOwnFeedRow } from "./feed";
import { ToolCallChip } from "../../shared/tool-calls/ToolCallChip";
import { statusFor } from "./data";
import { providerMeta } from "../../shared/providers";
import type { ApiConversation } from "./model";
import type { ConversationFeed } from "./useConversationFeed";
import { useHistoryScroll } from "./useHistoryScroll";
import { useEvidenceMessageFocus } from "./useEvidenceMessageFocus";
import type { ConversationListItem, ControlMode } from "./types";
import { SupervisionRevokedBanner } from "./SupervisionRevokedBanner";
import type { SupervisionRevocation } from "./supervision";
import { fmt, t } from "../../i18n";
import { pathFromRoute, routeFromPath } from "../../router";
import "./history-layout.css";
import { useConversationRuns } from "../integrations/runs/conversationContext";
import { ManualActionMenu } from "../integrations/runs/ManualActionMenu";
import { RunFeedCard } from "../integrations/runs/RunFeedCard";
import { mergeRunFeed } from "../integrations/runs/feed";

export function ConversationThread({ controlMode, dialog, detail, feed, isOwner = false, onClaim, onRelease, onClose, onSpam, onReturnQueue, canDelete = false, onDelete, onDiagnosticError, onToggleContext, onMobileBack, onExpandList, viewerId = null, onUpdated, onRefresh, retainsReplyAfterTransfer = false, revocation, onBack }: { controlMode: ControlMode; dialog: ConversationListItem | null; detail: ApiConversation | null; feed: ConversationFeed; isOwner?: boolean; onClaim: () => void; onRelease: () => void; onClose: () => void; onSpam: () => Promise<boolean>; onReturnQueue: () => void; canDelete?: boolean; onDelete: () => Promise<boolean>; onDiagnosticError: (error: string) => void; onToggleContext?: () => void; onMobileBack?: () => void; onExpandList?: () => void; viewerId?: number | null; onUpdated: (next: ApiConversation) => void; onRefresh: () => void; retainsReplyAfterTransfer?: boolean; revocation?: SupervisionRevocation | null; onBack?: () => void }) {
  const transfer = useConversationTransfer(detail, onUpdated, onRefresh, retainsReplyAfterTransfer);
  const timelineRef = useRef<HTMLDivElement>(null);
  // Сообщения переписки и внутренние комментарии — одна лента по времени.
  const services = useConversationRuns();
  const rows = useMemo(() => mergeRunFeed(feed.rows, services?.runs ?? [], feed.hasOlder, services?.hasMore ?? false), [feed.rows, feed.hasOlder, services?.runs, services?.hasMore]);
  const entries = useMemo(() => rows.map((row) => ({ key: row.key, own: row.kind !== "service_run" && isOwnFeedRow(row, viewerId) })), [rows, viewerId]);
  // Лента держит низ при новых репликах и догружает предыдущие при подходе к
  // верху, сохраняя место чтения.
  const { onScroll } = useHistoryScroll(timelineRef, {
    conversationId: dialog?.id ?? null,
    entries,
    hasOlder: feed.hasOlder || (services?.hasMore ?? false),
    loadingOlder: feed.loadingOlder || (services?.loading ?? false),
    loadOlder: () => { if (feed.hasOlder) feed.loadOlder(); if (services?.hasMore) void services.loadOlder(); },
  });
  useEvidenceMessageFocus(dialog?.id ?? null, feed);

  if (!dialog) {
    return <div className="sales-timeline"><div className="sales-timeline-inner"><div className="sales-wait-note">{t("conversations.pick_conversation")}</div></div></div>;
  }
  const status = statusFor(detail?.access?.isParticipant && !detail.isAssignedToViewer ? "assigned" : controlMode, detail?.assignedOperator?.name);
  const channel = providerMeta[dialog.channel];
  const qualityHref = detail?.lifecycle === "CLOSED" && (canDelete || detail.access?.supervised)
    ? pathFromRoute("qualityAnalysis", dialog.id, routeFromPath(window.location.pathname).organizationPublicId) : undefined;
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
              {detail?.hasAgent && <><i /><span className="is-agent" style={{ color: dialog.agentColor }}><Icon name="robot" size={13} />{dialog.agentName}</span></>}
              {dialog.groupName && <><i /><span>{dialog.groupName}</span></>}
            </p>
          </div>
        </div>
        <div className="sales-conversation-actions">
          <ManualActionMenu />
          {transfer.available && <TransferAction onOpen={transfer.open} />}
          {/* Одно действие взятия (решение 2): очередь и AI — primary; у другого
              сотрудника — вторичная кнопка; «ведёте вы» — «Вернуть AI». */}
          {detail?.access?.canControl && (controlMode === "waiting" || controlMode === "ai") && (
            <button className="sales-claim-button" onClick={onClaim}><Icon name="check" size={15} />{t("conversations.take_conversation")}</button>
          )}
          {controlMode === "assigned" && detail?.access?.canControl && <button className="sales-secondary-action" onClick={onClaim}>{t("conversations.take_conversation")}</button>}
          {controlMode === "human" && detail?.canReleaseToAi && detail?.access?.canControl && detail.isAssignedToViewer && <button className="sales-secondary-action" onClick={onRelease}>{t("conversations.hand_back_ai")}</button>}
          {detail?.access?.isParticipant && !detail.isAssignedToViewer && <span className="participant-chip" title={t("participants.chip_title")}><Icon name="team" size={14} />{t("participants.chip")}</span>}
          {/* Кадр S2: на узком экране контекст-панель — выдвижная, кнопка в шапке. */}
          {onToggleContext && <IconButton icon="user" label={t("conversations.conversation_context")} className="ctx-toggle" onClick={onToggleContext} />}
          <ConversationActions qualityHref={qualityHref} open={detail?.lifecycle === "OPEN" && !!detail.access?.canControl} canReturnQueue={controlMode === "human"} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} canDelete={canDelete} onDelete={onDelete} conversationId={dialog.id} canExportDiagnostics={canDelete} onDiagnosticError={onDiagnosticError} onTransfer={transfer.available ? transfer.open : undefined} />
        </div>
      </div>
      <div className="sales-timeline" ref={timelineRef} onScroll={onScroll}>
        <div className="sales-timeline-inner">
          {revocation && onBack && <SupervisionRevokedBanner loss={revocation} onBack={onBack} />}
          {feed.loaded && rows.length === 0 && <div className="sales-wait-note">{t("conversations.no_messages_yet")}</div>}
          {rows.map((row, index) => (
            <Fragment key={row.key}>
              {(index === 0 || !sameDay(rows[index - 1].createdAt, row.createdAt)) && (
                <div className="sales-day-divider"><span />{dayLabel(row.createdAt)}<span /></div>
              )}
              {row.kind === "service_run" ? <RunFeedCard run={row.run} /> : row.kind === "comment"
                ? <ConversationComment comment={row.comment} viewerId={viewerId} />
                : row.calls
                  ? <ToolCallChip calls={row.calls} createdAt={row.createdAt} />
                  : <span id={`message-${row.message.id}`} style={{ display: "contents" }}><ConversationMessage message={row.message} dialog={dialog} viewerId={viewerId} /></span>}
            </Fragment>
          ))}
        </div>
      </div>
      {transfer.overlay}
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
