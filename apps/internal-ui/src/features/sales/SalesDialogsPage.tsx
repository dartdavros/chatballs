import { useState } from "react";

import { ConversationWorkspace } from "../../features/conversations/ConversationWorkspace";
import { SalesContextPanel } from "./dialogs/SalesContextPanel";
import type { SalesRightTab } from "./dialogs/context/SalesContextTabs";

export function SalesDialogsPage({ initialConversationId }: { initialConversationId?: number | null }) {
  const [rightTab, setRightTab] = useState<SalesRightTab>("client");
  return (
    <ConversationWorkspace
      department="sales"
      initialConversationId={initialConversationId}
      renderContextPanel={({ dialog, detail }) => (
        <SalesContextPanel rightTab={rightTab} setRightTab={setRightTab} dialog={dialog} detail={detail} />
      )}
    />
  );
}
