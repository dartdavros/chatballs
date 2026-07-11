import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

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
  releaseConversation,
  returnToQueue,
  toConversationListItem,
  type ApiConversation,
} from "./model";
import type { ConversationListItem, ListTab } from "./types";
import { useConversationCall } from "./useConversationCall";

// Общий workspace диалогов (SPEC-HUB-0010 §8.2): sales и support используют его.
// Параметризуется department (изоляция inbox §10 + фильтр fetchConversations),
// заголовком/placeholder поиска и правой панелью через render-prop: consumer
// получает {dialog, detail} из state (sales рендерит лид-контекст, support —
// operator_cards из контракта).
export function ConversationWorkspace({ department, listTitle, searchPlaceholder, renderContextPanel, initialConversationId }: {
  department: "sales" | "support";
  listTitle?: string;
  searchPlaceholder?: string;
  renderContextPanel: (ctx: { dialog: ConversationListItem | null; detail: ApiConversation | null }) => ReactNode;
  initialConversationId?: number | null;
}) {
  const [listTab, setListTab] = useState<ListTab>("all");
  const [search, setSearch] = useState("");
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(initialConversationId ?? null);
  const [detail, setDetail] = useState<ApiConversation | null>(null);

  const loadList = useCallback(async () => {
    try {
      const items = await fetchConversations(department);
      setConversations(items);
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    } catch {
      /* keep previous list on transient errors */
    }
  }, [department]);

  const loadDetail = useCallback(async (id: number) => {
    try {
      setDetail(await fetchConversation(id));
    } catch {
      /* ignore */
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
    void loadDetail(selectedId);
    const timer = setInterval(() => loadDetail(selectedId), 3000);
    return () => clearInterval(timer);
  }, [selectedId, loadDetail]);

  const onConversationChanged = useCallback(() => {
    if (selectedId != null) void loadDetail(selectedId);
  }, [loadDetail, selectedId]);
  const callController = useConversationCall({ conversationId: selectedId, onConversationChanged });

  const dialogs = useMemo(() => conversations.map(toConversationListItem), [conversations]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return dialogs.filter((dialog) => {
      if (query && !`${dialog.name} ${dialog.product} ${dialog.preview}`.toLowerCase().includes(query)) return false;
      if (listTab === "wait") return dialog.mode === "wait";
      if (listTab === "ai") return dialog.mode === "ai";
      if (listTab === "operator") return dialog.mode === "operator";
      if (listTab === "unread") return dialog.unread > 0;
      return true;
    });
  }, [dialogs, listTab, search]);

  const selectedDialog = dialogs.find((dialog) => dialog.id === selectedId) ?? null;
  const controlMode = detail ? controlModeOf(detail) : "ai";

  function applyUpdated(updated: ApiConversation) {
    setDetail(updated);
    void loadList();
  }

  const onClaim = async () => {
    if (selectedId == null) return;
    try { applyUpdated(await claimConversation(selectedId)); } catch { /* ignore */ }
  };
  const onRelease = async () => {
    if (selectedId == null) return;
    try { applyUpdated(await releaseConversation(selectedId)); } catch { /* ignore */ }
  };
  const onReturnQueue = async () => {
    if (selectedId == null) return;
    try { applyUpdated(await returnToQueue(selectedId)); } catch { /* ignore */ }
  };
  const onClose = async () => {
    if (selectedId == null) return;
    try { applyUpdated(await closeConversation(selectedId)); } catch { /* ignore */ }
  };

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
        setSearch={setSearch}
        setListTab={setListTab}
        setSelectedId={setSelectedId}
      />
      <section className="sales-conversation">
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} onClaim={onClaim} onCall={() => void callController.start()} />
        <CallOverlay
          open={callController.open}
          dialog={selectedDialog}
          call={callController.call}
          access={callController.access}
          errorText={callController.errorText}
          onCallChange={callController.setCall}
          onCancel={() => void callController.cancel()}
          onRetry={() => void callController.retry()}
          onClose={callController.close}
        />
        <Composer
          mode={controlMode}
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
