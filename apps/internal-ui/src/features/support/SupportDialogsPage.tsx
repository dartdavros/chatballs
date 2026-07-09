import { useState } from "react";

import { ConversationWorkspace } from "../conversations/ConversationWorkspace";
import { SupportContextPanel, type SupportRightTab } from "./context/SupportContextPanel";

export function SupportDialogsPage({ initialConversationId }: { initialConversationId?: number | null }) {
  const [rightTab, setRightTab] = useState<SupportRightTab>("client");
  return (
    <ConversationWorkspace
      department="support"
      listTitle="Обращения"
      searchPlaceholder="Поиск по клиенту, продукту…"
      initialConversationId={initialConversationId}
      renderContextPanel={({ detail }) => (
        <SupportContextPanel rightTab={rightTab} setRightTab={setRightTab} detail={detail} />
      )}
    />
  );
}
