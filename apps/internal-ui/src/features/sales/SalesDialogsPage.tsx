import { useState } from "react";

import { ConversationWorkspace } from "../../features/conversations/ConversationWorkspace";
import type { SessionUser } from "../../types";
import { SalesContextPanel } from "./dialogs/SalesContextPanel";
import type { SalesRightTab } from "./dialogs/context/SalesContextTabs";

export function SalesDialogsPage({ initialConversationId, user }: { initialConversationId?: number | null; user: SessionUser }) {
  const [rightTab, setRightTab] = useState<SalesRightTab>("client");
  return (
    <ConversationWorkspace
      department="sales"
      isOwner={user.role === "OWNER"}
      initialConversationId={initialConversationId}
      renderContextPanel={({ dialog, detail }) => (
        <SalesContextPanel rightTab={rightTab} setRightTab={setRightTab} dialog={dialog} detail={detail} />
      )}
    />
  );
}
