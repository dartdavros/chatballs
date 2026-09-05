import { useEffect, useRef } from "react";

import { useAudioCue } from "@chatballs/ui";

import type { ApiConversation } from "./model";

const NOTIFICATION_SOUND = "/audio/notification.mp3";

export function useIncomingMessageSound(conversations: ApiConversation[], loaded: boolean) {
  const lastMessageIds = useRef(new Map<number, number>());
  const initialized = useRef(false);
  const playNotification = useAudioCue(NOTIFICATION_SOUND);

  useEffect(() => {
    if (!loaded) return;
    const next = new Map<number, number>();
    let hasIncoming = false;

    for (const conversation of conversations) {
      const message = conversation.lastMessage;
      if (!message) continue;
      next.set(conversation.id, message.id);
      const previousId = lastMessageIds.current.get(conversation.id) ?? 0;
      if (initialized.current && message.id > previousId && message.author === "CONTACT") hasIncoming = true;
    }

    lastMessageIds.current = next;
    if (!initialized.current) initialized.current = true;
    else if (hasIncoming) playNotification();
  }, [conversations, loaded, playNotification]);
}
