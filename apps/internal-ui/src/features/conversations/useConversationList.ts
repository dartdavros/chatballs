import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchConversations,
  type ApiConversation,
  type ConversationListQuery,
} from "./model";

// Инбокс — живая лента: сверху приходит окно, вниз оно догружается прокруткой.
// Обновление перезапрашивает только голову списка (туда попадает вся свежая
// активность) и вклеивает её в уже загруженное, не сбрасывая прокрутку.
const LIST_WINDOW = 30;
const REFRESH_INTERVAL_MS = 4000;
// С живыми оповещениями опрос остаётся только страховкой.
const REFRESH_IDLE_INTERVAL_MS = 30000;

export type ConversationListState = {
  conversations: ApiConversation[];
  total: number;
  loaded: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  errorText: string;
  loadMore: () => void;
  refresh: () => Promise<void>;
};

/** Голова списка заменяет свои строки в уже загруженном хвосте: диалог, который
 *  поднялся наверх после нового сообщения, не должен остаться и внизу. */
export function mergeHead(
  head: ApiConversation[],
  tail: ApiConversation[],
): ApiConversation[] {
  const fresh = new Set(head.map((conversation) => conversation.id));
  return [...head, ...tail.filter((conversation) => !fresh.has(conversation.id))];
}

export function useConversationList(
  query: ConversationListQuery,
  { live = false }: { live?: boolean } = {},
): ConversationListState {
  const [conversations, setConversations] = useState<ApiConversation[]>([]);
  const [total, setTotal] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [errorText, setErrorText] = useState("");
  // Запрос сравнивается по значению: объект фильтров пересоздаётся на каждый
  // рендер, и по ссылке эффект перезапускался бы бесконечно.
  const key = JSON.stringify(query);
  const stableQuery = useMemo(() => JSON.parse(key) as ConversationListQuery, [key]);
  const loadingMoreRef = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const page = await fetchConversations({ ...stableQuery, limit: LIST_WINDOW });
      setConversations((current) => mergeHead(page.items, current));
      setTotal(page.total);
      // Курсор и признак продолжения принадлежат прокрутке: обновление головы
      // не знает, докуда пользователь уже долистал, и не должно их сбрасывать.
      setLoaded(true);
      setErrorText("");
    } catch {
      setErrorText("Не удалось обновить список диалогов");
    }
  }, [stableQuery]);

  useEffect(() => {
    let active = true;
    setConversations([]);
    setLoaded(false);
    setHasMore(false);
    setCursor(null);
    fetchConversations({ ...stableQuery, limit: LIST_WINDOW })
      .then((page) => {
        if (!active) return;
        setConversations(page.items);
        setTotal(page.total);
        setHasMore(page.hasMore);
        setCursor(page.cursor);
        setLoaded(true);
        setErrorText("");
      })
      .catch(() => {
        if (active) setErrorText("Не удалось загрузить список диалогов");
      });
    return () => {
      active = false;
    };
  }, [stableQuery]);

  useEffect(() => {
    const timer = setInterval(
      () => void refresh(),
      live ? REFRESH_IDLE_INTERVAL_MS : REFRESH_INTERVAL_MS,
    );
    return () => clearInterval(timer);
  }, [live, refresh]);

  const loadMore = useCallback(() => {
    if (cursor == null || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    fetchConversations({ ...stableQuery, cursor, limit: LIST_WINDOW })
      .then((page) => {
        setConversations((current) => mergeHead(current, page.items));
        setHasMore(page.hasMore);
        setCursor(page.cursor);
        setTotal(page.total);
        setErrorText("");
      })
      .catch(() => setErrorText("Не удалось загрузить следующие диалоги"))
      .finally(() => {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      });
  }, [cursor, stableQuery]);

  return { conversations, total, loaded, hasMore, loadingMore, errorText, loadMore, refresh };
}
