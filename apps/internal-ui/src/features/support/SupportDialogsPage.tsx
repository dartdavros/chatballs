import { useState } from "react";

import { ConversationWorkspace } from "../conversations/ConversationWorkspace";
import type { EmployeeGroup, SessionUser } from "../../types";
import { SupportContextPanel, type SupportRightTab } from "./context/SupportContextPanel";

export function SupportDialogsPage({ initialConversationId, user, groups = [], employees = [] }: { initialConversationId?: number | null; user: SessionUser; groups?: EmployeeGroup[]; employees?: Array<{ id: number; name: string }> }) {
  const [rightTab, setRightTab] = useState<SupportRightTab>("client");
  return (
    <ConversationWorkspace
      isOwner={user.role === "OWNER"}
      listTitle="Обращения"
      searchPlaceholder="Поиск по клиенту, продукту…"
      initialConversationId={initialConversationId}
      renderContextPanel={({ detail, applyConversation }) => (
        <SupportContextPanel rightTab={rightTab} setRightTab={setRightTab} detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} />
      )}
    />
  );
}
