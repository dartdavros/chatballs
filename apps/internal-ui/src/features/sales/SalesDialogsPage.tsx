import { useState } from "react";

import { ConversationWorkspace } from "../../features/conversations/ConversationWorkspace";
import type { EmployeeGroup, SessionUser } from "../../types";
import { SalesContextPanel } from "./dialogs/SalesContextPanel";
import type { SalesRightTab } from "./dialogs/context/SalesContextTabs";

export function SalesDialogsPage({ initialConversationId, user, groups = [], employees = [] }: { initialConversationId?: number | null; user: SessionUser; groups?: EmployeeGroup[]; employees?: Array<{ id: number; name: string }> }) {
  const [rightTab, setRightTab] = useState<SalesRightTab>("client");
  return (
    <ConversationWorkspace
      isOwner={user.role === "OWNER"}
      initialConversationId={initialConversationId}
      renderContextPanel={({ dialog, detail, applyConversation }) => (
        <SalesContextPanel rightTab={rightTab} setRightTab={setRightTab} dialog={dialog} detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} />
      )}
    />
  );
}
