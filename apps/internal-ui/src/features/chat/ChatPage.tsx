import { useState, type ReactNode } from "react";

import { ConversationWorkspace, type DialogScope } from "../conversations/ConversationWorkspace";
import { DialogControls } from "../conversations/DialogControls";
import type { ApiConversation, ConversationCounters } from "../conversations/model";
import type { ConversationListItem } from "../conversations/types";
import { ClientContext } from "../sales/dialogs/context/ClientContext";
import { HistoryContext } from "../sales/dialogs/context/HistoryContext";
import { OperatorCards } from "../support/context/OperatorCards";
import { SupportHistory } from "../support/context/SupportHistory";
import type { EmployeeGroup, SessionUser } from "../../types";

// Единый «Чат» (дизайн-базлайн v2 §8.1): один экран для всех диалогов
// организации. Контекст-панель сама выбирает представление по источнику
// identity диалога: sales-контакт или verified support-снапшот.

type ChatRightTab = "client" | "history";

export function ChatPage({
  initialConversationId,
  user,
  groups = [],
  employees = [],
  scope,
  setScope,
  counters,
  showScopeSwitcher,
}: {
  initialConversationId?: number | null;
  user: SessionUser;
  groups?: EmployeeGroup[];
  employees?: Array<{ id: number; name: string }>;
  scope: DialogScope;
  setScope: (scope: DialogScope) => void;
  counters: ConversationCounters | null;
  showScopeSwitcher: boolean;
}) {
  const [rightTab, setRightTab] = useState<ChatRightTab>("client");
  return (
    <ConversationWorkspace
      isOwner={user.role === "OWNER"}
      initialConversationId={initialConversationId}
      scope={scope}
      setScope={setScope}
      counters={counters}
      showScopeSwitcher={showScopeSwitcher}
      renderContextPanel={({ dialog, detail, applyConversation }) => (
        <ChatContextPanel
          rightTab={rightTab}
          setRightTab={setRightTab}
          dialog={dialog}
          detail={detail}
          groups={groups}
          employees={employees}
          applyConversation={applyConversation}
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
}: {
  rightTab: ChatRightTab;
  setRightTab: (tab: ChatRightTab) => void;
  dialog: ConversationListItem | null;
  detail: ApiConversation | null;
  groups: EmployeeGroup[];
  employees: Array<{ id: number; name: string }>;
  applyConversation: (updated: ApiConversation) => void;
}) {
  const isSupport = Boolean(detail?.supportIdentitySnapshot);
  return (
    <section className="sales-context">
      <div className="sales-context-tabs">
        <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Контакт</RightTabButton>
        <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
      </div>
      <div className="sales-context-body">
        {rightTab === "client" && (
          isSupport ? (
            <>
              {detail && (
                <DialogControls detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} />
              )}
              <OperatorCards detail={detail} />
            </>
          ) : (
            <ClientContext dialog={dialog} detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} />
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
