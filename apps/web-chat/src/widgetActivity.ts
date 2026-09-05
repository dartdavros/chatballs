import { useEffect } from "react";

import { useAudioCue, useLoopingAudio } from "@chatballs/ui";

const NOTIFICATION_SOUND = "/chat/audio/notification.mp3";
const RINGTONE_SOUND = "/chat/audio/ringtone.mp3";

type WidgetActivity =
  | { type: "chatballs-chat-activity"; kind: "message" }
  | { type: "chatballs-chat-activity"; kind: "call"; active: boolean };

function postActivity(activity: WidgetActivity) {
  window.parent.postMessage(activity, "*");
}

export function useWidgetActivity(incomingCall: boolean) {
  const embedded = window.parent !== window;
  const playNotification = useAudioCue(NOTIFICATION_SOUND);

  useLoopingAudio(RINGTONE_SOUND, !embedded && incomingCall);

  useEffect(() => {
    if (embedded) postActivity({ type: "chatballs-chat-activity", kind: "call", active: incomingCall });
  }, [embedded, incomingCall]);

  return () => {
    if (embedded) postActivity({ type: "chatballs-chat-activity", kind: "message" });
    else playNotification();
  };
}
