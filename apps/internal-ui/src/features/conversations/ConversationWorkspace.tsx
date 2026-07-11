import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { CallOverlay } from "./CallOverlay";
import { Composer } from "./Composer";
import { ConversationThread } from "./ConversationThread";
import { DialogList } from "./DialogList";
import {
  cancelCall,
  claimConversation,
  closeConversation,
  controlModeOf,
  fetchActiveCall,
  fetchCall,
  fetchConversation,
  fetchConversations,
  releaseConversation,
  requestCall,
  returnToQueue,
  toConversationListItem,
  type ApiCall,
  type ApiConversation,
} from "./model";
import type { ConversationListItem, ListTab } from "./types";

const TERMINAL_CALL_STATUSES = new Set(["DECLINED", "CANCELLED", "MISSED", "ENDED", "FAILED", "EXPIRED"]);

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
  // Онлайн-звонок текущего диалога: оверлей по baseline «Экран звонка».
  const [callOpen, setCallOpen] = useState(false);
  const [call, setCall] = useState<ApiCall | null>(null);
  const [callError, setCallError] = useState("");
  const [callBusy, setCallBusy] = useState(false);

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

  // Смена диалога сбрасывает оверлей звонка.
  useEffect(() => {
    setCallOpen(false);
    setCall(null);
    setCallError("");
  }, [selectedId]);

  // Поллинг состояния звонка, пока оверлей открыт и звонок не завершён.
  const callId = call?.id ?? null;
  const callStatus = call?.status ?? null;
  useEffect(() => {
    if (!callOpen || callId == null || callStatus == null || TERMINAL_CALL_STATUSES.has(callStatus)) return;
    const timer = setInterval(async () => {
      try {
        setCall(await fetchCall(callId));
      } catch {
        /* transient */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [callOpen, callId, callStatus]);

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

  // Запрос онлайн-звонка (§6): если в диалоге уже есть незавершённый звонок —
  // открываем его состояние; иначе создаём (backend атомарно перехватит AI).
  const onCall = async () => {
    if (selectedId == null || callBusy) return;
    setCallBusy(true);
    setCallError("");
    try {
      const active = await fetchActiveCall(selectedId);
      const next = active ?? (await requestCall(selectedId));
      setCall(next);
      if (selectedId != null) void loadDetail(selectedId);
    } catch (error) {
      setCall(null);
      setCallError(error instanceof Error ? error.message : "Не удалось запросить звонок");
    } finally {
      setCallBusy(false);
      setCallOpen(true);
    }
  };

  const onCallCancel = async () => {
    if (call == null) return;
    try {
      setCall(await cancelCall(call.id));
      if (selectedId != null) void loadDetail(selectedId);
    } catch { /* поллинг подтянет фактическое состояние */ }
    setCallOpen(false);
  };

  const onCallRetry = async () => {
    if (selectedId == null) return;
    setCall(null);
    setCallError("");
    try {
      setCall(await requestCall(selectedId));
      void loadDetail(selectedId);
    } catch (error) {
      setCallError(error instanceof Error ? error.message : "Не удалось запросить звонок");
    }
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
        <ConversationThread controlMode={controlMode} dialog={selectedDialog} detail={detail} onClaim={onClaim} onCall={() => void onCall()} />
        <CallOverlay
          open={callOpen}
          dialog={selectedDialog}
          call={call}
          errorText={callError}
          onCancel={() => void onCallCancel()}
          onRetry={() => void onCallRetry()}
          onClose={() => setCallOpen(false)}
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
