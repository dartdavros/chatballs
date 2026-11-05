import { useEffect, useRef, useState } from "react";
import { t } from "./i18n";
import { useAudioCapture } from "./speech/useAudioCapture";

export type VoiceRecorderState = "idle" | "permission" | "recording" | "sending";

export function useVoiceRecorder({ onSend, maxBytes = 10 * 1024 * 1024 }: {
  onSend: (audio: Blob, durationSeconds: number) => Promise<void>; maxBytes?: number;
}) {
  const [sending, setSending] = useState(false);
  const [errorText, setErrorText] = useState("");
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const capture = useAudioCapture({
    maxBytes,
    onError: () => setErrorText(t("chat.no_mic_access")),
    onComplete: (audio, seconds) => {
      setSending(true);
      void onSend(audio, seconds).catch((error) => {
        if (mounted.current) setErrorText(error instanceof Error ? error.message : t("chat.could_not_send_voice"));
      }).finally(() => { if (mounted.current) setSending(false); });
    },
  });
  const state: VoiceRecorderState = sending ? "sending" : capture.phase;
  return {
    supported: typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia),
    state, seconds: capture.seconds, errorText,
    start: async () => { if (!sending) { setErrorText(""); await capture.start(); } },
    stopAndSend: capture.stop, cancel: capture.cancel,
  };
}