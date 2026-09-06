import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { CallOverlay } from "./CallOverlay";
import { Composer } from "./Composer";
import { ConversationThread } from "./ConversationThread";
import { DialogList, type ListSort } from "./DialogList";
import {
  claimConversation,
  closeConversation,
  controlModeOf,
  fetchConversation,
  fetchConversations,
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
  if (scope.kind === "ungrouped") return "Без группы";
  if (scope.kind === "agent") return scope.label;
  if (scope.kind === "assignee") return scope.label;
  return "Все диалоги";
}
import type { ConversationListItem, ListTab } from "./types";
import { useConversationCall } from "./useConversationCall";
import { useIncomingMessageSound } from "./useIncomingMessageSound";

// Общий workspace диалогов (SPEC-HUB-0010 §8.2). Видимость inbox решает
// backend по группам (ADR-HUB-0043); страница параметризуется заголовком,
// placeholder поиска и правой панелью через render-prop.
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
  // Кадр S2: на ≤1024px контекст-панель — выдвижная поверх ленты.
  const [ctxOpen, setCtxOpen] = useState(false);
  // Кадры M1/M2: на ≤768px список и лента — отдельные экраны.
  const [mobileDialogOpen, setMobileDialogOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);
  const [search, setSearch] = useState("");
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [listLoaded, setListLoaded] = useState(false);
  const [listError, setListError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(initialConversationId ?? null);
  const [detail, setDetail] = useState<ApiConversation | null>(null);
  const [detailError, setDetailError] = useState("");
  const [actionError, setActionError] = useState("");
  const selectedIdRef = useRef<number | null>(selectedId);
  selectedIdRef.current = selectedId;

  const loadList = useCallback(async () => {
    try {
      const items = await fetchConversations(scopeFilters(scope));
      setConversations(items);
      setListLoaded(true);
      setListError("");
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    } catch {
      setListError("Не удалось обновить список диалогов");
    }
  }, [scope]);

  const loadDetail = useCallback(async (id: number) => {
    try {
      const loaded = await fetchConversation(id);
      if (selectedIdRef.current === id) {
        setDetail(loaded);
        setDetailError("");
      }
    } catch {
      if (selectedIdRef.current === id) {
        setDetailError("Не удалось загрузить диалог");
      }
    }
  }, []);

  useEffect(() => {
    void loadList();
    const timer = setInterval(loadList, 4000);
    return () => clearInterval(timer);
  }, [loadList]);

  useEffect(() => {
    if (initialConversationId != null) setSelectedId(initialConversationId);
  }, [initialConversationId]);

  useEffect(() => {
    setCtxOpen(false);
  }, [selectedId]);

  useEffect(() => {
    if (selectedId == null) return;
    setDetail(null);
    setDetailError("");
    setActionError("");
    void loadDetail(selectedId);
    const timer = setInterval(() => loadDetail(selectedId), 3000);
    return () => clearInterval(timer);
  }, [selectedId, loadDetail]);

  const onConversationChanged = useCallback(() => {
    if (selectedId != null) void loadDetail(selectedId);
  }, [loadDetail, selectedId]);
  const callController = useConversationCall({ conversationId: selectedId, onConversationChanged });
  useIncomingMessageSound(conversations, listLoaded);

  // Клавиатура (SPEC-HUB-0031 §9): ↑/↓ — по списку, Enter — открыть (мобайл),
  // «/» — фокус в поиск. Не перехватываем ввод в полях.
  const filteredRef = useRef<ConversationListItem[]>([]);
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, [contenteditable], .ant-dropdown")) return;
      if (event.key === "/") {
        event.preventDefault();
        searchRef.current?.focus();
        return;
      }
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        const list = filteredRef.current;
        if (!list.length) return;
        event.preventDefault();
        const index = list.findIndex((dialog) => dialog.id === selectedIdRef.current);
        const next = event.key === "ArrowDown"
          ? list[Math.min(index + 1, list.length - 1)]
          : list[Math.max(index - 1, 0)];
        if (next) setSelectedId(next.id);
        return;
      }
      if (event.key === "Enter" && selectedIdRef.current != null) {
        setMobileDialogOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Сортировка и сворачивание списка (заголовок списка, кадр A1).
  const [sort, setSort] = useState<ListSort>("activity");
  const [listCollapsed, setListCollapsed] = useState(false);
  const dialogs = useMemo(() => conversations.map(toConversationListItem), [conversations]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const items = dialogs.filter((dialog) => {
      if (query && !`${dialog.name} ${dialog.email} ${dialog.product} ${dialog.preview}`.toLowerCase().includes(query)) return false;
      if (listTab === "wait") return dialog.mode === "wait";
      if (listTab === "mine") return dialog.isMine;
      return true;
    });
    if (sort === "waiting") {
      // Ждущие оператора — первыми, дольше всех ждущие — выше; остальные по активности.
      const activity = (dialog: ConversationListItem) => conversations.find((c) => c.id === dialog.id)?.lastActivityAt ?? "";
      return [...items].sort((a, b) => {
        if ((a.mode === "wait") !== (b.mode === "wait")) return a.mode === "wait" ? -1 : 1;
        return a.mode === "wait" ? activity(a).localeCompare(activity(b)) : activity(b).localeCompare(activity(a));
      });
    }
    return items;
  }, [conversations, dialogs, listTab, search, sort]);

  filteredRef.current = filtered;
  const selectedDialog = dialogs.find((dialog) => dialog.id === selectedId) ?? null;
  const detailLoaded = detail?.id === selectedId;
  const controlMode = detailLoaded ? controlModeOf(detail) : "waiting";

  function applyUpdated(updated: ApiConversation) {
    setDetail(updated);
    setActionError("");
    void loadList();
  }

  async function updateConversation(action: (id: number) => Promise<ApiConversation>): Promise<boolean> {
    if (selectedId == null) return false;
    setActionError("");
    try {
      applyUpdated(await action(selectedId));
      return true;
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Не удалось выполнить действие");
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
        filtered={filtered}
        listTab={listTab}
        selectedId={selectedId ?? -1}
        search={search}
        errorText={listError}
        setSearch={setSearch}
        setListTab={setListTab}
        setSelectedId={(id) => {
          setSelectedId(id);
          setMobileDialogOpen(true);
        }}
        mobileHeader={mobileHeader}
        hint={hint}
        searchRef={searchRef}
      />
      {!selectedDialog && (
        <section className="sales-conversation"><div className="sales-conversation-empty">Выберите диалог</div></section>
      )}
      {selectedDialog && (
      <section className="sales-conversation" key={selectedDialog.id}>
        {ctxOpen && <button className="ctx-backdrop" type="button" aria-label="Закрыть панель" onClick={() => setCtxOpen(false)} />}
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} isOwner={isOwner} onExpandList={listCollapsed ? () => setListCollapsed(false) : undefined} viewerId={viewerId} onClaim={onClaim} onRelease={onRelease} onClose={onClose} onSpam={onSpam} onReturnQueue={onReturnQueue} onArchive={onArchive} onToggleContext={() => setCtxOpen((open) => !open)} onMobileBack={() => setMobileDialogOpen(false)} />
        {(detailError || actionError) && <div className="sales-conversation-error">{detailError || actionError}</div>}
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
          onSent={() => selectedId != null && loadDetail(selectedId)}
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
