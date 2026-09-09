import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../../i18n";

// Запись голосового в композере (дизайн-базлайн v2, кадр H): MediaRecorder,
// таймер, отмена/отправка. Формат — opus (ogg в Firefox, webm в Chromium).

export type VoiceRecorderState = "idle" | "recording" | "sending";

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const candidate of ["audio/ogg;codecs=opus", "audio/webm;codecs=opus", "audio/webm"]) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return "";
}

export function useVoiceRecorder({ onSend }: { onSend: (audio: Blob, durationSeconds: number) => Promise<void> }) {
  const [state, setState] = useState<VoiceRecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [errorText, setErrorText] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef(0);
  const discardRef = useRef(false);

  const supported = typeof MediaRecorder !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia);

  const cleanupStream = useCallback(() => {
    recorderRef.current?.stream.getTracks().forEach((track) => track.stop());
    recorderRef.current = null;
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => () => {
    discardRef.current = true;
    recorderRef.current?.state !== "inactive" && recorderRef.current?.stop();
    cleanupStream();
  }, [cleanupStream]);

  const start = useCallback(async () => {
    if (!supported || state !== "idle") return;
    setErrorText("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, pickMimeType() ? { mimeType: pickMimeType() } : undefined);
      chunksRef.current = [];
      discardRef.current = false;
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      });
      recorder.addEventListener("stop", () => {
        const duration = (Date.now() - startedAtRef.current) / 1000;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        cleanupStream();
        if (discardRef.current || blob.size === 0 || duration < 0.5) {
          setState("idle");
          setSeconds(0);
          return;
        }
        setState("sending");
        onSend(blob, duration)
          .then(() => {
            setState("idle");
            setSeconds(0);
          })
          .catch((error) => {
            setErrorText(error instanceof Error ? error.message : t("conversations.could_not_send_voice_message"));
            setState("idle");
            setSeconds(0);
          });
      });
      recorderRef.current = recorder;
      startedAtRef.current = Date.now();
      recorder.start();
      setState("recording");
      setSeconds(0);
      timerRef.current = window.setInterval(() => {
        setSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000));
      }, 250);
    } catch {
      setErrorText(t("conversations.no_access_microphone"));
    }
  }, [cleanupStream, onSend, state, supported]);

  const stopAndSend = useCallback(() => {
    if (recorderRef.current?.state === "recording") {
      discardRef.current = false;
      recorderRef.current.stop();
    }
  }, []);

  const cancel = useCallback(() => {
    if (recorderRef.current?.state === "recording") {
      discardRef.current = true;
      recorderRef.current.stop();
    }
  }, []);

  return { supported, state, seconds, errorText, start, stopAndSend, cancel };
}
