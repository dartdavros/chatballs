import { useEffect, useState } from "react";

import type { DialogScope } from "../conversations/ConversationWorkspace";
import { fetchConversationCounters, type ConversationCounters } from "../conversations/model";

// Охват чата (дерево «Все диалоги · Группы · Агенты») живёт на уровне Shell:
// у сотрудника им управляет сайдбар, у менеджера — поповер в заголовке списка.
export function useChatScope(enabled: boolean) {
  const [scope, setScope] = useState<DialogScope>({ kind: "all" });
  const [counters, setCounters] = useState<ConversationCounters | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const load = () =>
      fetchConversationCounters()
        .then((payload) => {
          if (!cancelled) setCounters(payload);
        })
        .catch(() => undefined);
    void load();
    const timer = setInterval(load, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [enabled]);

  return { scope, setScope, counters };
}
