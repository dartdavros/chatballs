import type { ReactNode } from "react";
import { CallOverlay } from "./CallOverlay";
import { Composer } from "./Composer";
import { ConversationThread } from "./ConversationThread";
import { DialogList } from "./DialogList";
import { IconButton } from "../../shared/ui-controls";
import type { ApiConversation, ConversationCounters } from "./model";
import type { ConversationListItem } from "./types";
import type { DialogScope } from "./workspaceScope";
import { useConversationWorkspace } from "./useConversationWorkspace";
import { t } from "../../i18n";
export type { DialogScope } from "./workspaceScope";
export { scopeLabel } from "./workspaceScope";

export function ConversationWorkspace({ isOwner = false, canDelete = false, viewerId = null, listTitle, searchPlaceholder, renderContextPanel, mobileHeader, hint, initialConversationId, scope, setScope, counters, showScopeSwitcher = true, sender }: {
  isOwner?: boolean;
  /** Удалять диалоги могут владелец и администратор (то же проверяет сервер). */
  canDelete?: boolean;
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
  sender?: { operatorName: string; company: string };
}) {
  const {
    listTab, setListTab, sort, setSort, ctxOpen, setCtxOpen, mobileDialogOpen,
    setMobileDialogOpen, listCollapsed, setListCollapsed, search, setSearch,
    selectedId, setSelectedId, detail, detailError, actionError, setActionError,
    settledSearch, list, history, callController, dialogs, selectedDialog,
    detailLoaded, controlMode, applyUpdated,
    onClaim, onRelease, onReturnQueue, onClose, onSpam, onDelete,
  } = useConversationWorkspace({ initialConversationId, scope, counters, viewerId });

  return (
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
          setSelectedId(id);
          setMobileDialogOpen(true);
        }}
        mobileHeader={mobileHeader}
        hint={hint}
      />
      {!selectedDialog && (
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
      <section className="sales-conversation enter-surface" key={selectedDialog.id}>
        {ctxOpen && <button className="ctx-backdrop" type="button" aria-label={t("admin.close_panel")} onClick={() => setCtxOpen(false)} />}
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} history={history} isOwner={isOwner} onExpandList={listCollapsed ? () => setListCollapsed(false) : undefined} viewerId={viewerId} onClaim={onClaim} onRelease={onRelease} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} canDelete={canDelete} onDelete={onDelete} onDiagnosticError={setActionError} onToggleContext={() => setCtxOpen((open) => !open)} onMobileBack={() => setMobileDialogOpen(false)} />
        {(detailError || actionError || history.errorText) && <div className="sales-conversation-error">{detailError || actionError || history.errorText}</div>}
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
          mode={controlMode}
          channel={selectedDialog?.channel}
          voiceAllowed={detail?.connection?.voiceMessages ?? false}
          templateValues={{
            client_name: detail?.contact?.isGuest ? "" : detail?.contact?.name,
            operator_name: sender?.operatorName,
            company: sender?.company,
          }}
          loaded={detailLoaded}
          assignedOperatorName={detail?.assignedOperator?.name}
          conversationId={selectedId}
          onClaim={onClaim}
          onRelease={onRelease}
          onReturnQueue={onReturnQueue}
          onClose={onClose}
          onSent={() => { void history.catchUp(); void list.refresh(); }}
        />
      </section>
      )}
      {selectedDialog && renderContextPanel({
        dialog: selectedDialog,
        detail,
        applyConversation: applyUpdated,
        // Звонки — в карточке контакта (решение 5); доступность по точке входа
        // («Настройки → Голосовые и звонки»), почта звонков не поддерживает.
        startCall: detail?.lifecycle === "OPEN" && (detail.connection?.audioCalls || detail.connection?.videoCalls) ? (kind) => void callController.start(kind) : null,
        // Кадр S2: выдвижная панель закрывается крестиком в её шапке.
        closeContext: () => setCtxOpen(false),
        assignmentTimeoutMinutes: counters?.assignmentTimeoutMinutes,
      })}
    </div>
  );
}
