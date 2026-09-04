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
  fetchConversations,
  markConversationAsSpam,
  releaseConversation,
  returnToQueue,
  toConversationListItem,
  type ApiConversation,
} from "./model";
import type { ConversationListItem, ListTab } from "./types";
import { useConversationCall } from "./useConversationCall";
import { useIncomingMessageSound } from "./useIncomingMessageSound";

// Общий workspace диалогов (SPEC-HUB-0010 §8.2). Видимость inbox решает
// backend по группам (ADR-HUB-0043); страница параметризуется заголовком,
// placeholder поиска и правой панелью через render-prop.
export function ConversationWorkspace({ isOwner = false, listTitle, searchPlaceholder, renderContextPanel, initialConversationId }: {
  isOwner?: boolean;
  listTitle?: string;
  searchPlaceholder?: string;
  renderContextPanel: (ctx: { dialog: ConversationListItem | null; detail: ApiConversation | null }) => ReactNode;
  initialConversationId?: number | null;
}) {
  const [listTab, setListTab] = useState<ListTab>("all");
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
      const items = await fetchConversations();
      setConversations(items);
      setListLoaded(true);
      setListError("");
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    } catch {
      setListError("Не удалось обновить список диалогов");
    }
  }, []);

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

  const dialogs = useMemo(() => conversations.map(toConversationListItem), [conversations]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return dialogs.filter((dialog) => {
      if (query && !`${dialog.name} ${dialog.email} ${dialog.product} ${dialog.preview}`.toLowerCase().includes(query)) return false;
      if (listTab === "wait") return dialog.mode === "wait";
      if (listTab === "ai") return dialog.mode === "ai";
      if (listTab === "operator") return dialog.mode === "operator";
      if (listTab === "unread") return dialog.unread > 0;
      return true;
    });
  }, [dialogs, listTab, search]);

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

  return (
    <div className="sales-dialogs">
      <DialogList
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
        setSelectedId={setSelectedId}
      />
      <section className="sales-conversation">
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} isOwner={isOwner} onClaim={onClaim} onCall={(kind) => void callController.start(kind)} onClose={onClose} onSpam={onSpam} />
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
      {renderContextPanel({ dialog: selectedDialog, detail })}
    </div>
  );
}
