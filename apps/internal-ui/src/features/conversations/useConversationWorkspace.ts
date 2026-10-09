import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { controlModeOf, fetchConversation, toConversationListItem, type ApiConversation, type ConversationCounters } from "./model";
import type { ListSort, ListTab } from "./types";
import { scopeFilters, type DialogScope } from "./workspaceScope";
import { useConversationCall } from "./useConversationCall";
import { useConversationEvents } from "./useConversationEvents";
import { useConversationActions } from "./useConversationActions";
import { useDebounced } from "../../shared/useDebounced";
import { useOpenedConversationRead } from "../notifications/useOpenedConversationRead";
import { useConversationHistory } from "./useConversationHistory";
import { useConversationList } from "./useConversationList";
import { useDialogKeyboardNav } from "./useDialogKeyboardNav";
import { useIncomingMessageSound } from "./useIncomingMessageSound";
import { t } from "../../i18n";

export function useConversationWorkspace({ initialConversationId, scope, counters, viewerId }: {
  initialConversationId?: number | null; scope: DialogScope;
  counters: ConversationCounters | null; viewerId: number | null;
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
    ...(listTab === "queue" ? { queue: true } : {}),
    ...(listTab === "onMe" ? { waitingOnMe: true } : {}),
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
    } catch (error) {
      if (selectedIdRef.current !== id) return;
      // Диалог удалили — возможно, другим администратором. Карточки больше
      // нет, и держать выбор не на чем; список обновит событие инбокса.
      if (error instanceof ApiError && error.status === 404) {
        setSelectedId(null);
        setDetail(null);
        setDetailError("");
        return;
      }
      setDetailError(t("conversations.could_not_load_conversation"));
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

  useOpenedConversationRead(selectedId);

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

  const dialogs = useMemo(
    () => list.conversations.map((item) => toConversationListItem(item, { viewerId, assignmentTimeoutMinutes: counters?.assignmentTimeoutMinutes })),
    [list.conversations, viewerId, counters?.assignmentTimeoutMinutes],
  );
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

  const actions = useConversationActions({
    selectedId, applyUpdated, setError: setActionError,
    clearSelected: () => { setDetail(null); setSelectedId(null); void list.refresh(); },
  });
  return {
    listTab, setListTab, sort, setSort, ctxOpen, setCtxOpen, mobileDialogOpen,
    setMobileDialogOpen, listCollapsed, setListCollapsed, search, setSearch,
    selectedId, setSelectedId, detail, detailError, actionError, setActionError,
    settledSearch, list, history, callController, dialogs, selectedDialog,
    detailLoaded, controlMode, applyUpdated, ...actions,
  };
}
