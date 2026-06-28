import { useCallback, useEffect, useMemo, useState } from "react";

import { SalesComposer } from "./dialogs/SalesComposer";
import { SalesContextPanel } from "./dialogs/SalesContextPanel";
import { SalesConversation } from "./dialogs/SalesConversation";
import { SalesDialogList } from "./dialogs/SalesDialogList";
import {
  claimConversation,
  controlModeOf,
  fetchConversation,
  fetchConversations,
  releaseConversation,
  toDialog,
  type ApiConversation,
} from "./dialogs/model";
import type { ListTab, RightTab } from "./dialogs/types";

export function SalesDialogsPage({ initialConversationId }: { initialConversationId?: number | null }) {
  const [listTab, setListTab] = useState<ListTab>("all");
  const [rightTab, setRightTab] = useState<RightTab>("client");
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(initialConversationId ?? null);
  const [detail, setDetail] = useState<ApiConversation | null>(null);

  const loadList = useCallback(async () => {
    try {
      const items = await fetchConversations();
      setConversations(items);
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    } catch {
      /* keep previous list on transient errors */
    }
  }, []);

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

  const dialogs = useMemo(() => conversations.map(toDialog), [conversations]);
  const filtered = useMemo(
    () =>
      dialogs.filter((dialog) => {
        if (listTab === "wait") return dialog.mode === "wait";
        if (listTab === "ai") return dialog.mode === "ai";
        if (listTab === "operator") return dialog.mode === "operator";
        if (listTab === "unread") return dialog.unread > 0;
        return true;
      }),
    [dialogs, listTab],
  );

  const selectedDialog = dialogs.find((dialog) => dialog.id === selectedId) ?? null;
  const controlMode = detail ? controlModeOf(detail) : "ai";

  function applyUpdated(updated: ApiConversation) {
    setDetail(updated);
    void loadList();
  }

  const onClaim = async () => {
    if (selectedId == null) return;
    try {
      applyUpdated(await claimConversation(selectedId));
    } catch {
      /* ignore */
    }
  };
  const onRelease = async () => {
    if (selectedId == null) return;
    try {
      applyUpdated(await releaseConversation(selectedId));
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="sales-dialogs">
      <SalesDialogList
        dialogs={dialogs}
        filtered={filtered}
        listTab={listTab}
        selectedId={selectedId ?? -1}
        setListTab={setListTab}
        setSelectedId={setSelectedId}
      />
      <section className="sales-conversation">
        <SalesConversation controlMode={controlMode} dialog={selectedDialog} detail={detail} onClaim={onClaim} />
        <SalesComposer
          mode={controlMode}
          conversationId={selectedId}
          onClaim={onClaim}
          onRelease={onRelease}
          onSent={() => selectedId != null && loadDetail(selectedId)}
        />
      </section>
      <SalesContextPanel rightTab={rightTab} setRightTab={setRightTab} dialog={selectedDialog} detail={detail} />
    </div>
  );
}
