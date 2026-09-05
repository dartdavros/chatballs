import { useEffect, useState, type ReactNode } from "react";

import { ChatMobileHeader } from "../../layout/ChatMobileHeader";
import { Hint } from "../../shared/Hint";
import { Icon } from "../../shared/icons";

import { ConversationWorkspace, type DialogScope } from "../conversations/ConversationWorkspace";
import { DialogControls } from "../conversations/DialogControls";
import { fetchChatDirectory, type ApiConversation, type ChatDirectory, type ConversationCounters } from "../conversations/model";
import type { ConversationListItem } from "../conversations/types";
import { ClientContext } from "../sales/dialogs/context/ClientContext";
import { HistoryContext } from "../sales/dialogs/context/HistoryContext";
import { OperatorCards } from "../support/context/OperatorCards";
import { SupportHistory } from "../support/context/SupportHistory";
import type { EmployeeGroupRef, RouteKey, SessionUser } from "../../types";

// Единый «Чат» (дизайн-базлайн v2 §8.1): один экран для всех диалогов
// организации. Контекст-панель сама выбирает представление по источнику
// identity диалога: sales-контакт или verified support-снапшот.

type ChatRightTab = "client" | "history";

export function ChatPage({
  initialConversationId,
  user,
  scope,
  setScope,
  counters,
  showScopeSwitcher,
  setRoute,
  onLogout,
  onOpenMenu,
}: {
  initialConversationId?: number | null;
  user: SessionUser;
  scope: DialogScope;
  setScope: (scope: DialogScope) => void;
  counters: ConversationCounters | null;
  showScopeSwitcher: boolean;
  setRoute: (route: RouteKey) => void;
  onLogout: () => void;
  onOpenMenu: () => void;
}) {
  const [rightTab, setRightTab] = useState<ChatRightTab>("client");
  const [directory, setDirectory] = useState<ChatDirectory>({ groups: [], employees: [] });
  useEffect(() => {
    let cancelled = false;
    fetchChatDirectory().then((payload) => { if (!cancelled) setDirectory(payload); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [user.organizationPublicId]);
  return (
    <ConversationWorkspace
      isOwner={user.role === "OWNER"}
      initialConversationId={initialConversationId}
      scope={scope}
      setScope={setScope}
      counters={counters}
      showScopeSwitcher={showScopeSwitcher}
      mobileHeader={({ total }) => <ChatMobileHeader user={user} scope={scope} total={total} setRoute={setRoute} onLogout={onLogout} onOpenMenu={onOpenMenu} />}
      hint={showScopeSwitcher
        ? <Hint id="chat-visibility">Вы видите все диалоги организации. Сотрудники видят только диалоги своих групп, без группы и те, где они ответственные.</Hint>
        : undefined}
      viewerId={user.id}
      renderContextPanel={({ dialog, detail, applyConversation, startCall, closeContext }) => (
        <ChatContextPanel
          rightTab={rightTab}
          setRightTab={setRightTab}
          dialog={dialog}
          detail={detail}
          groups={directory.groups}
          employees={directory.employees}
          applyConversation={applyConversation}
          startCall={startCall}
          closeContext={closeContext}
          viewerId={user.id}
        />
      )}
    />
  );
}

function ChatContextPanel({
  rightTab,
  setRightTab,
  dialog,
  detail,
  groups,
  employees,
  applyConversation,
  startCall,
  closeContext,
  viewerId,
}: {
  rightTab: ChatRightTab;
  setRightTab: (tab: ChatRightTab) => void;
  dialog: ConversationListItem | null;
  detail: ApiConversation | null;
  groups: EmployeeGroupRef[];
  employees: Array<{ id: number; name: string }>;
  applyConversation: (updated: ApiConversation) => void;
  startCall: ((kind: "AUDIO" | "VIDEO") => void) | null;
  closeContext: () => void;
  viewerId: number;
}) {
  const isSupport = Boolean(detail?.supportIdentitySnapshot);
  return (
    <section className="sales-context">
      <div className="sales-context-tabs">
        <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Контакт</RightTabButton>
        <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
        <button className="ctx-close" type="button" aria-label="Закрыть панель" onClick={closeContext}><Icon name="xCircle" size={16} /></button>
      </div>
      <div className="sales-context-body">
        {rightTab === "client" && (
          isSupport ? (
            <>
              {detail && (
                <DialogControls detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} viewerId={viewerId} />
              )}
              <OperatorCards detail={detail} />
            </>
          ) : (
            <ClientContext dialog={dialog} detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} startCall={startCall} viewerId={viewerId} />
          )
        )}
        {rightTab === "history" && (isSupport ? <SupportHistory detail={detail} /> : <HistoryContext detail={detail} />)}
      </div>
    </section>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}
