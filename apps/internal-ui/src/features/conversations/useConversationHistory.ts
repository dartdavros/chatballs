import { useCallback, useEffect, useRef, useState } from "react";

import { fetchMessages, type ApiMessage } from "./model";
import { t } from "../../i18n";

// Открытие диалога показывает хвост переписки; вверх история догружается по
// прокрутке, вниз — дельтой обновления. Целиком лента не запрашивается никогда:
// в диалоге может быть сколько угодно сообщений.
const HISTORY_WINDOW = 50;
// Пока оповещения живы, опрос — только страховка на случай потерянного события.
const DELTA_INTERVAL_MS = 3000;
const DELTA_IDLE_INTERVAL_MS = 30000;

export type ConversationHistory = {
  messages: ApiMessage[];
  loaded: boolean;
  hasOlder: boolean;
  loadingOlder: boolean;
  errorText: string;
  loadOlder: () => void;
  /** Подтянуть то, что появилось после последнего показанного сообщения. */
  catchUp: () => Promise<void>;
};

function mergeNewer(current: ApiMessage[], incoming: ApiMessage[]): ApiMessage[] {
  if (incoming.length === 0) return current;
  const known = new Set(current.map((message) => message.id));
  const fresh = incoming.filter((message) => !known.has(message.id));
  return fresh.length ? [...current, ...fresh] : current;
}

export function useConversationHistory(
  conversationId: number | null,
  { live = false }: { live?: boolean } = {},
): ConversationHistory {
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [hasOlder, setHasOlder] = useState(false);
  const [olderCursor, setOlderCursor] = useState<number | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [errorText, setErrorText] = useState("");
  // Курсор дельты — последний показанный id; ref, чтобы поллинг не пересоздавался
  // на каждое новое сообщение.
  const lastIdRef = useRef(0);
  const conversationRef = useRef<number | null>(conversationId);
  conversationRef.current = conversationId;

  useEffect(() => {
    if (conversationId == null) {
      setMessages([]);
      setLoaded(false);
      setHasOlder(false);
      setOlderCursor(null);
      lastIdRef.current = 0;
      return;
    }
    let active = true;
    setMessages([]);
    setLoaded(false);
    setHasOlder(false);
    setOlderCursor(null);
    setErrorText("");
    lastIdRef.current = 0;
    fetchMessages(conversationId, { limit: HISTORY_WINDOW })
      .then((page) => {
        if (!active || conversationRef.current !== conversationId) return;
        setMessages(page.items);
        setHasOlder(page.hasMore);
        setOlderCursor(page.cursor);
        setLoaded(true);
        lastIdRef.current = page.items.length ? page.items[page.items.length - 1].id : 0;
      })
      .catch(() => {
        if (active && conversationRef.current === conversationId) setErrorText(t("conversations.could_not_load_conversation_history"));
      });
    return () => {
      active = false;
    };
  }, [conversationId]);

  const catchUp = useCallback(async () => {
    const id = conversationRef.current;
    if (id == null || lastIdRef.current === 0) return;
    try {
      const page = await fetchMessages(id, { after: lastIdRef.current });
      if (conversationRef.current !== id || page.items.length === 0) return;
      lastIdRef.current = page.items[page.items.length - 1].id;
      setMessages((current) => mergeNewer(current, page.items));
      setErrorText("");
    } catch {
      setErrorText(t("conversations.could_not_refresh_conversation_history"));
    }
  }, []);

  useEffect(() => {
    if (conversationId == null || !loaded) return;
    const timer = setInterval(
      () => void catchUp(),
      live ? DELTA_IDLE_INTERVAL_MS : DELTA_INTERVAL_MS,
    );
    return () => clearInterval(timer);
  }, [catchUp, conversationId, live, loaded]);

  const loadOlder = useCallback(() => {
    const id = conversationRef.current;
    if (id == null || olderCursor == null || loadingOlder) return;
    setLoadingOlder(true);
    fetchMessages(id, { before: olderCursor, limit: HISTORY_WINDOW })
      .then((page) => {
        if (conversationRef.current !== id) return;
        setMessages((current) => [...page.items, ...current]);
        setHasOlder(page.hasMore);
        setOlderCursor(page.cursor);
        setErrorText("");
      })
      .catch(() => {
        if (conversationRef.current === id) setErrorText(t("conversations.could_not_load_earlier_messages"));
      })
      .finally(() => {
        if (conversationRef.current === id) setLoadingOlder(false);
      });
  }, [loadingOlder, olderCursor]);

  return { messages, loaded, hasOlder, loadingOlder, errorText, loadOlder, catchUp };
}
