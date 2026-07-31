import { useState } from "react";

import { ConversationWorkspace } from "../conversations/ConversationWorkspace";
import type { SessionUser } from "../../types";
import { SupportContextPanel, type SupportRightTab } from "./context/SupportContextPanel";

export function SupportDialogsPage({ initialConversationId, user }: { initialConversationId?: number | null; user: SessionUser }) {
  const [rightTab, setRightTab] = useState<SupportRightTab>("client");
  return (
    <ConversationWorkspace
      department="support"
      isOwner={user.role === "OWNER"}
      listTitle="Обращения"
      searchPlaceholder="Поиск по клиенту, продукту…"
      initialConversationId={initialConversationId}
      renderContextPanel={({ detail }) => (
        <SupportContextPanel rightTab={rightTab} setRightTab={setRightTab} detail={detail} />
      )}
    />
  );
}
