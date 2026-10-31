import { useCallback, type ReactNode } from "react";
import { CallOverlay } from "./CallOverlay";
import { Composer } from "./Composer";
import { EmailContinuationProvider } from "./EmailContinuationContext";
import { ConversationAccessLost } from "./ConversationAccessLost";
import { ConversationThread } from "./ConversationThread";
import { DialogList } from "./DialogList";
import { IconButton } from "../../shared/ui-controls";
import { fetchConversation, type ApiConversation, type ConversationCounters } from "./model";
import type { ConversationListItem } from "./types";
import type { DialogScope } from "./workspaceScope";
import { useConversationWorkspace } from "./useConversationWorkspace";
import { t } from "../../i18n";
import { conversationAction } from "./supervision";
import { ConversationRunsProvider } from "../integrations/runs/ConversationRunsProvider";
import { ConversationRunPanel } from "../integrations/runs/ConversationRunPanel";
export type { DialogScope } from "./workspaceScope";
export { scopeLabel } from "./workspaceScope";

export function ConversationWorkspace({ isOwner = false, canDelete = false, retainsReplyAfterTransfer = false, viewerId = null, listTitle, searchPlaceholder, renderContextPanel, mobileHeader, hint, initialConversationId, scope, setScope, counters, showScopeSwitcher = true }: {
  isOwner?: boolean;
  /** Удалять диалоги могут владелец и администратор (то же проверяет сервер). */
  canDelete?: boolean;
  /** Меняет только пояснение: разрешённые действия по-прежнему задаёт API. */
  retainsReplyAfterTransfer?: boolean;
  listTitle?: string;
  searchPlaceholder?: string;
  renderContextPanel: (ctx: { dialog: ConversationListItem | null; detail: ApiConversation | null; applyConversation: (updated: ApiConversation) => void; startCall: ((kind: "AUDIO" | "VIDEO") => void) | null; closeContext: () => void; assignmentTimeoutMinutes?: number }) => ReactNode;
  viewerId?: number | null;
  mobileHeader?: (info: { total: number }) => ReactNode;
  hint?: ReactNode;
  initialConversationId?: number | null;
  // Охват (дерево фильтров) живёт в Shell: у сотрудника им управляет сайдбар,
  // у менеджера — поповер в заголовке списка.
  scope: DialogScope;
  setScope: (scope: DialogScope) => void;
  counters: ConversationCounters | null;
  showScopeSwitcher?: boolean;
  /** Кто отвечает — для переменных шаблонов ответов. */
}) {
  const {
    listTab, setListTab, sort, setSort, ctxOpen, setCtxOpen, mobileDialogOpen,
    setMobileDialogOpen, listCollapsed, setListCollapsed, search, setSearch,
    selectedId, setSelectedId, detail, detailError, actionError, setActionError,
    settledSearch, list, feed, callController, dialogs, selectedDialog,
    detailLoaded, controlMode, applyUpdated, accessLost, setAccessLost, revocation, clearRevocation,
    onClaim, onRelease, onReturnQueue, onClose, onSpam, onDelete,
  } = useConversationWorkspace({ initialConversationId, scope, counters, viewerId });
  const openRunContext = useCallback(() => setCtxOpen(true), [setCtxOpen]);

  return (
    <ConversationRunsProvider conversationId={detail?.id ?? null} openContext={openRunContext}>
    <div className={`sales-dialogs ${ctxOpen ? "is-ctx-open" : ""} ${mobileDialogOpen ? "is-mobile-dialog" : ""} ${listCollapsed ? "is-list-collapsed" : ""}`}>
      <DialogList
        viewerId={viewerId}
        sort={sort}
        setSort={setSort}
        onCollapse={() => setListCollapsed(true)}
        scope={scope}
        counters={counters}
        setScope={setScope}
        showScopeSwitcher={showScopeSwitcher}
        title={listTitle}
        searchPlaceholder={searchPlaceholder}
        dialogs={dialogs}
        total={list.total}
        hasMore={list.hasMore}
        onLoadMore={list.loadMore}
        narrowed={Boolean(settledSearch) || listTab !== "all"}
        listTab={listTab}
        selectedId={selectedId ?? -1}
        search={search}
        errorText={list.errorText}
        setSearch={setSearch}
        setListTab={setListTab}
        setSelectedId={(id) => {
          setAccessLost("");
          setSelectedId(id);
          setMobileDialogOpen(true);
        }}
        mobileHeader={mobileHeader}
        hint={hint}
      />
      {accessLost && <ConversationAccessLost detail={accessLost} onBack={() => setAccessLost("")} />}
      {!selectedDialog && !accessLost && (
        <section className="sales-conversation">
          {/* Свёрнутый список без выбранного диалога: вернуть его больше неоткуда —
              шапки переписки, где живёт та же кнопка, здесь нет. */}
          {listCollapsed && (
            <div className="sales-conversation-head">
              <IconButton bare icon="collapseLeft" iconSize={17} label={t("conversations.show_list")} className="list-expand" onClick={() => setListCollapsed(false)} />
            </div>
          )}
          <div className="sales-conversation-empty">{t("conversations.pick_conversation")}</div>
        </section>
      )}
      {selectedDialog && (
      <EmailContinuationProvider key={selectedDialog.id} id={selectedDialog.id} enabled={selectedDialog.channel === "WEB"} messageIds={feed.rows.flatMap((row) => row.kind === "message" ? [row.message.id] : [])}>
      <section className="sales-conversation enter-surface" key={selectedDialog.id}>
        {ctxOpen && <button className="ctx-backdrop" type="button" aria-label={t("admin.close_panel")} onClick={() => setCtxOpen(false)} />}
        <ConversationThread revocation={revocation} onBack={clearRevocation} retainsReplyAfterTransfer={retainsReplyAfterTransfer} onUpdated={applyUpdated} onRefresh={() => { if (selectedId != null) void fetchConversation(selectedId).then(applyUpdated).catch(() => void list.refresh()); }} controlMode={controlMode} dialog={selectedDialog} detail={detail} feed={feed} isOwner={isOwner} onExpandList={listCollapsed ? () => setListCollapsed(false) : undefined} viewerId={viewerId} onClaim={onClaim} onRelease={onRelease} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} canDelete={canDelete} onDelete={onDelete} onDiagnosticError={setActionError} onToggleContext={() => setCtxOpen((open) => !open)} onMobileBack={() => setMobileDialogOpen(false)} />
        {!revocation && (detailError || actionError || feed.errorText) && <div className="sales-conversation-error">{detailError || actionError || feed.errorText}</div>}
        <CallOverlay
          open={callController.open}
          dialog={selectedDialog}
          call={callController.call}
          requestedKind={callController.requestedKind}
          access={callController.access}
          errorText={callController.errorText}
          onCallChange={callController.setCall}
          onCancel={() => void callController.cancel()}
          onRetry={() => void callController.retry()}
          onClose={callController.close}
        />
        <Composer
          supervised={detail?.access?.supervised}
          canControl={detail?.access?.canControl ?? false}
          canComment={conversationAction(detail, "conversations.comment")}
          revoked={Boolean(revocation)}
          mode={controlMode}
          channel={selectedDialog?.channel}
          contactId={detail?.contact?.id}
          voiceAllowed={detail?.connection?.voiceMessages ?? false}
          assistanceEnabled={detail?.replyAssistanceEnabled ?? false}
          agentName={detail?.hasAgent ? selectedDialog.agentName : ""}
          loaded={detailLoaded}
          assignedOperatorName={detail?.assignedOperator?.name}
          isParticipant={detail?.access?.isParticipant && !detail.isAssignedToViewer}
          conversationId={selectedId}
          clientName={selectedDialog.name}
          onClaim={onClaim}
          onRelease={onRelease}
          onReturnQueue={onReturnQueue}
          onClose={onClose}
          onSent={() => { void feed.catchUpMessages(); void list.refresh(); }}
          onCommentSaved={() => void feed.catchUpComments()}
        />
      </section>
      </EmailContinuationProvider>
      )}
      {selectedDialog && <ConversationRunPanel>{renderContextPanel({
        dialog: selectedDialog,
        detail,
        applyConversation: applyUpdated,
        // Звонки — в карточке контакта (решение 5); доступность по точке входа
        // («Настройки → Голосовые и звонки»), почта звонков не поддерживает.
        startCall: detail?.access?.actions.includes("conversations.call") && detail.lifecycle === "OPEN" && (detail.connection?.audioCalls || detail.connection?.videoCalls) ? (kind) => void callController.start(kind) : null,
        // Кадр S2: выдвижная панель закрывается крестиком в её шапке.
        closeContext: () => setCtxOpen(false),
        assignmentTimeoutMinutes: counters?.assignmentTimeoutMinutes,
      })}</ConversationRunPanel>}
    </div>
    </ConversationRunsProvider>
  );
}
