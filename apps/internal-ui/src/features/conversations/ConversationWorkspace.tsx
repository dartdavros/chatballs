import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { CallOverlay } from "./CallOverlay";
import { Composer } from "./Composer";
import { ConversationThread } from "./ConversationThread";
import { DialogList } from "./DialogList";
import {
  claimConversation,
  closeConversation,
  controlModeOf,
  fetchConversation,
  markConversationAsSpam,
  releaseConversation,
  setConversationArchived,
  returnToQueue,
  toConversationListItem,
  type ApiConversation,
  type ConversationCounters,
  type ConversationListFilters,
} from "./model";
export type DialogScope =
  | { kind: "all" }
  | { kind: "group"; id: number; label: string }
  | { kind: "ungrouped" }
  | { kind: "agent"; id: number; label: string }
  | { kind: "assignee"; id: number; label: string };

function scopeFilters(scope: DialogScope): ConversationListFilters {
  if (scope.kind === "group") return { group: String(scope.id) };
  if (scope.kind === "ungrouped") return { group: "none" };
  if (scope.kind === "agent") return { agent: scope.id };
  if (scope.kind === "assignee") return { assigned: scope.id };
  return {};
}

export function scopeLabel(scope: DialogScope): string {
  if (scope.kind === "group") return scope.label;
  if (scope.kind === "ungrouped") return t("common.no_group");
  if (scope.kind === "agent") return scope.label;
  if (scope.kind === "assignee") return scope.label;
  return t("profile.all_conversations");
}
import type { ConversationListItem, ListSort, ListTab } from "./types";
import { useConversationCall } from "./useConversationCall";
import { useConversationEvents } from "./useConversationEvents";
import { useDebounced } from "../../shared/useDebounced";
import { useConversationHistory } from "./useConversationHistory";
import { useConversationList } from "./useConversationList";
import { useDialogKeyboardNav } from "./useDialogKeyboardNav";
import { useIncomingMessageSound } from "./useIncomingMessageSound";
import { t } from "../../i18n";

// Общий workspace диалогов (SPEC-HUB-0010 §8.2). Видимость inbox решает
// backend по группам (ADR-CHATBALLS-0043); страница параметризуется заголовком,
// placeholder поиска и правой панелью через render-prop. Список и история —
// серверные окна: ни то, ни другое целиком не запрашивается.
export function ConversationWorkspace({ isOwner = false, viewerId = null, listTitle, searchPlaceholder, renderContextPanel, mobileHeader, hint, initialConversationId, scope, setScope, counters, showScopeSwitcher = true }: {
  isOwner?: boolean;
  listTitle?: string;
  searchPlaceholder?: string;
  renderContextPanel: (ctx: { dialog: ConversationListItem | null; detail: ApiConversation | null; applyConversation: (updated: ApiConversation) => void; startCall: ((kind: "AUDIO" | "VIDEO") => void) | null; closeContext: () => void }) => ReactNode;
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
}) {
  const [listTab, setListTab] = useState<ListTab>("all");
  const [sort, setSort] = useState<ListSort>("activity");
  // Кадр S2: на ≤1024px контекст-панель — выдвижная поверх ленты.
  const [ctxOpen, setCtxOpen] = useState(false);
  // Кадры M1/M2: на ≤768px список и лента — отдельные экраны.
  const [mobileDialogOpen, setMobileDialogOpen] = useState(false);
  const [listCollapsed, setListCollapsed] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(initialConversationId ?? null);
  const [detail, setDetail] = useState<ApiConversation | null>(null);
  const [detailError, setDetailError] = useState("");
  const [actionError, setActionError] = useState("");
  const selectedIdRef = useRef<number | null>(selectedId);
  selectedIdRef.current = selectedId;

  // Поиск, вкладка и порядок — параметры запроса: список приходит окном, и
  // фильтровать в браузере было бы нечего.
  // Ввод в поиске придерживается: запрос уходит, когда человек перестал печатать.
  const settledSearch = useDebounced(search.trim());
  const query = useMemo(() => ({
    ...scopeFilters(scope),
    ...(listTab === "wait" ? { waiting: true } : {}),
    ...(listTab === "mine" ? { assigned: "me" as const } : {}),
    ...(settledSearch ? { q: settledSearch } : {}),
    sort,
  }), [listTab, scope, settledSearch, sort]);
  // Оповещения ведут обновление, опрос остаётся страховкой: при обрыве сокета
  // всё возвращается к прежним интервалам само.
  const events = useConversationEvents({
    conversationId: selectedId,
    onInboxChanged: () => void list.refresh(),
    onConversationChanged: (changedId) => {
      if (changedId !== selectedIdRef.current) return;
      void history.catchUp();
      void loadDetail(changedId);
    },
  });
  const list = useConversationList(query, { live: events.connected });
  const history = useConversationHistory(selectedId, { live: events.connected });

  const loadDetail = useCallback(async (id: number) => {
    try {
      const loaded = await fetchConversation(id);
      if (selectedIdRef.current === id) {
        setDetail(loaded);
        setDetailError("");
      }
    } catch {
      if (selectedIdRef.current === id) setDetailError(t("conversations.could_not_load_conversation"));
    }
  }, []);

  useEffect(() => {
    if (initialConversationId != null) setSelectedId(initialConversationId);
  }, [initialConversationId]);

  useEffect(() => {
    setSelectedId((current) => current ?? list.conversations[0]?.id ?? null);
  }, [list.conversations]);

  useEffect(() => {
    setCtxOpen(false);
  }, [selectedId]);

  useEffect(() => {
    if (selectedId == null) return;
    setDetail(null);
    setDetailError("");
    setActionError("");
    void loadDetail(selectedId);
    // Карточка диалога (статус, ответственный, метки) обновляется отдельно от
    // ленты: сообщений она больше не несёт. С живыми оповещениями опрос — тоже
    // страховка.
    const timer = setInterval(() => loadDetail(selectedId), events.connected ? 30000 : 3000);
    return () => clearInterval(timer);
  }, [events.connected, selectedId, loadDetail]);

  const onConversationChanged = useCallback(() => {
    if (selectedId != null) void loadDetail(selectedId);
  }, [loadDetail, selectedId]);
  const callController = useConversationCall({ conversationId: selectedId, onConversationChanged });
  useIncomingMessageSound(list.conversations, list.loaded);

  const dialogs = useMemo(() => list.conversations.map(toConversationListItem), [list.conversations]);
  useDialogKeyboardNav({
    dialogs,
    selectedId,
    setSelectedId,
    onOpen: () => setMobileDialogOpen(true),
  });

  const selectedDialog = dialogs.find((dialog) => dialog.id === selectedId) ?? null;
  const detailLoaded = detail?.id === selectedId;
  const controlMode = detailLoaded ? controlModeOf(detail) : "waiting";

  function applyUpdated(updated: ApiConversation) {
    setDetail(updated);
    setActionError("");
    void list.refresh();
  }

  async function updateConversation(action: (id: number) => Promise<ApiConversation>): Promise<boolean> {
    if (selectedId == null) return false;
    setActionError("");
    try {
      applyUpdated(await action(selectedId));
      return true;
    } catch (error) {
      setActionError(error instanceof Error ? error.message : t("common.could_not_complete_action"));
      return false;
    }
  }

  const onClaim = () => { void updateConversation(claimConversation); };
  const onRelease = () => { void updateConversation(releaseConversation); };
  const onReturnQueue = () => { void updateConversation(returnToQueue); };
  const onClose = () => { void updateConversation(closeConversation); };
  const onSpam = () => updateConversation(markConversationAsSpam);
  const onArchive = async () => {
    const done = await updateConversation((id) => setConversationArchived(id, true));
    // Архивный диалог исчезает из списка — снимаем выбор.
    if (done) setSelectedId(null);
    return done;
  };

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
        <section className="sales-conversation"><div className="sales-conversation-empty">{t("conversations.pick_conversation")}</div></section>
      )}
      {selectedDialog && (
      <section className="sales-conversation enter-surface" key={selectedDialog.id}>
        {ctxOpen && <button className="ctx-backdrop" type="button" aria-label={t("admin.close_panel")} onClick={() => setCtxOpen(false)} />}
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} history={history} isOwner={isOwner} onExpandList={listCollapsed ? () => setListCollapsed(false) : undefined} viewerId={viewerId} onClaim={onClaim} onRelease={onRelease} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} onArchive={onArchive} onToggleContext={() => setCtxOpen((open) => !open)} onMobileBack={() => setMobileDialogOpen(false)} />
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
      })}
    </div>
  );
}
