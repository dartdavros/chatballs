import { useCallback, useLayoutEffect, useRef, type RefObject } from "react";

import type { ApiMessage } from "./model";

// Ближе этого к верхнему краю — подгружаем предыдущие сообщения.
const LOAD_TRIGGER_PX = 240;
// Дальше этого от низа считается, что человек читает историю: новое сообщение
// не должно дёргать ленту к последней реплике.
const STICK_TO_BOTTOM_PX = 200;

export type HistoryScroll = {
  onScroll: () => void;
};

/** Прокрутка ленты истории: держит низ при новых сообщениях, подгружает старые
 *  при подходе к верху и сохраняет место чтения, когда они вклеиваются сверху. */
export function useHistoryScroll(
  ref: RefObject<HTMLDivElement | null>,
  {
    conversationId,
    messages,
    hasOlder,
    loadingOlder,
    loadOlder,
  }: {
    conversationId: number | null;
    messages: ApiMessage[];
    hasOlder: boolean;
    loadingOlder: boolean;
    loadOlder: () => void;
  },
): HistoryScroll {
  const firstId = messages.length ? messages[0].id : 0;
  const lastId = messages.length ? messages[messages.length - 1].id : 0;
  // Высота ленты в момент запроса предыдущих сообщений: по разнице с новой
  // высотой возвращаем взгляд на ту же реплику.
  const anchorHeightRef = useRef<number | null>(null);
  const previousFirstIdRef = useRef(firstId);

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node || previousFirstIdRef.current === firstId) return;
    const anchorHeight = anchorHeightRef.current;
    previousFirstIdRef.current = firstId;
    if (anchorHeight == null) return;
    node.scrollTop += node.scrollHeight - anchorHeight;
    anchorHeightRef.current = null;
  }, [firstId, ref]);

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node || lastId === 0) return;
    const distanceToBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
    // Первый показ диалога и собственные ответы приводят ленту к последней
    // реплике; при чтении истории — оставляем как есть.
    if (distanceToBottom <= STICK_TO_BOTTOM_PX || anchorHeightRef.current !== null) return;
    node.scrollTop = node.scrollHeight;
  }, [lastId, ref]);

  useLayoutEffect(() => {
    const node = ref.current;
    if (node) node.scrollTop = node.scrollHeight;
    anchorHeightRef.current = null;
    previousFirstIdRef.current = 0;
  }, [conversationId, ref]);

  const onScroll = useCallback(() => {
    const node = ref.current;
    if (!node || !hasOlder || loadingOlder || anchorHeightRef.current !== null) return;
    if (node.scrollTop > LOAD_TRIGGER_PX) return;
    anchorHeightRef.current = node.scrollHeight;
    loadOlder();
  }, [hasOlder, loadOlder, loadingOlder, ref]);

  return { onScroll };
}
