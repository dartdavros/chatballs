import { useEffect, useRef, useState } from "react";

import { resolveWebSocketUrl } from "../../api/client";

// Оповещения о диалогах: сервер сообщает, что изменилось, клиент забирает
// данные обычным запросом. Поллинг остаётся запасным путём и замедляется, пока
// сокет жив, — при обрыве всё работает ровно как раньше.

const RECONNECT_MIN_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export type ConversationEvents = {
  /** Сокет открыт: поллинг можно замедлить. */
  connected: boolean;
};

export function useConversationEvents({
  conversationId,
  onInboxChanged,
  onConversationChanged,
}: {
  conversationId: number | null;
  onInboxChanged: () => void;
  onConversationChanged: (conversationId: number) => void;
}): ConversationEvents {
  const [connected, setConnected] = useState(false);
  // Обработчики пересоздаются на каждый рендер — держим их в ref, чтобы сокет
  // не переоткрывался вместе с ними.
  const inboxRef = useRef(onInboxChanged);
  inboxRef.current = onInboxChanged;
  const conversationRef = useRef(onConversationChanged);
  conversationRef.current = onConversationChanged;
  const socketRef = useRef<WebSocket | null>(null);
  const watchedRef = useRef<number | null>(null);

  useEffect(() => {
    const url = resolveWebSocketUrl("/conversations/");
    if (!url) return;
    let closed = false;
    let retry = RECONNECT_MIN_MS;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function open() {
      if (closed) return;
      const socket = new WebSocket(url as string);
      socketRef.current = socket;
      socket.onopen = () => {
        retry = RECONNECT_MIN_MS;
        setConnected(true);
        // После обрыва подписка теряется вместе с сокетом — восстанавливаем её.
        if (watchedRef.current != null) {
          socket.send(JSON.stringify({ type: "watch", conversationId: watchedRef.current }));
        }
      };
      socket.onmessage = (event) => {
        const payload = JSON.parse(String(event.data)) as { type?: string; conversationId?: number };
        if (payload.type === "inbox.changed") inboxRef.current();
        if (payload.type === "conversation.changed" && typeof payload.conversationId === "number") {
          conversationRef.current(payload.conversationId);
        }
      };
      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (closed) return;
        // Отступ растёт до полуминуты: сервер мог уйти на перезапуск.
        reconnectTimer = setTimeout(open, retry);
        retry = Math.min(retry * 2, RECONNECT_MAX_MS);
      };
      socket.onerror = () => socket.close();
    }

    open();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  useEffect(() => {
    watchedRef.current = conversationId;
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN && conversationId != null) {
      socket.send(JSON.stringify({ type: "watch", conversationId }));
    }
  }, [conversationId, connected]);

  return { connected };
}
