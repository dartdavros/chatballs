import { useEffect, useRef, useState } from "react";
import type { WebSpeechCapabilities } from "@chatballs/contracts";
import { recognize, RecognitionError } from "./api";
import { DraftAttempt } from "./draft";
import { useAudioCapture } from "./useAudioCapture";
import type { CaptureLimit } from "./capture";

export type DictationNotice = "permission" | "recording" | "recognizing" | "result" | "cancelled" | "unsupported" | "denied" | "formatError" | "emptySpeech" | "networkError" | "providerError" | "timeoutError" | "limitError";
const errorNotices: Record<string, DictationNotice> = {
  empty: "emptySpeech", timeout: "timeoutError", too_large: "limitError", too_long: "limitError", format_unsupported: "formatError",
};

export function useDictation({ token, hostOrigin, settings, onResult }: {
  token: string | null; hostOrigin: string; settings?: WebSpeechCapabilities; onResult: (text: string) => void;
}) {
  const [recognizing, setRecognizing] = useState(false);
  const [notice, setNotice] = useState<DictationNotice | null>(null);
  const [limit, setLimit] = useState<CaptureLimit>(null);
  const [retryable, setRetryable] = useState(false);
  const attempt = useRef(new DraftAttempt());
  const controller = useRef<AbortController | null>(null);
  const recording = useRef<Blob | null>(null);
  const append = useRef(onResult);
  append.current = onResult;

  function discardRequest() { attempt.current.cancel(); controller.current?.abort(); controller.current = null; }

  async function transcribe(audio: Blob, stoppedBy: CaptureLimit = null) {
    if (!token) return;
    discardRequest();
    const id = attempt.current.begin();
    const pending = new AbortController();
    controller.current = pending;
    recording.current = audio;
    setRecognizing(true); setRetryable(false); setNotice("recognizing"); setLimit(stoppedBy);
    const timeout = setTimeout(() => pending.abort("timeout"), 55000);
    try {
      const text = await recognize(token, audio, hostOrigin, pending.signal);
      if (attempt.current.accept(id, text, (result) => append.current(result))) {
        recording.current = null; setNotice("result");
      }
    } catch (error) {
      if (!attempt.current.current(id)) return;
      setNotice(pending.signal.reason === "timeout" ? "timeoutError"
        : error instanceof RecognitionError ? errorNotices[error.code] || "providerError" : "networkError");
      setRetryable(true);
    } finally {
      clearTimeout(timeout);
      if (attempt.current.current(id)) { setRecognizing(false); controller.current = null; }
    }
  }

  const capture = useAudioCapture({
    maxBytes: settings?.maxRecordingBytes ?? 10 * 1024 * 1024,
    maxSeconds: settings?.maxDictationSeconds ?? 60,
    onComplete: (audio, _seconds, stoppedBy) => { void transcribe(audio, stoppedBy); },
    onError: setNotice,
  });

  useEffect(() => {
    capture.cancel();
    discardRequest(); recording.current = null;
    setRecognizing(false); setRetryable(false); setNotice(null);
    return () => { discardRequest(); recording.current = null; };
  }, [token, settings?.microphoneMode, settings?.available]);

  function cancel() {
    discardRequest(); capture.cancel(); recording.current = null;
    setRecognizing(false); setRetryable(false); setLimit(null); setNotice(null);
  }

  return {
    notice: capture.phase !== "idle" ? capture.phase : notice, seconds: capture.seconds, limit, retryable,
    recording: capture.phase === "recording",
    busy: recognizing || capture.phase !== "idle",
    available: settings?.microphoneMode === "dictation" && settings.available,
    maxSeconds: settings?.maxDictationSeconds ?? 60,
    maxBytes: settings?.maxRecordingBytes ?? 10 * 1024 * 1024,
    start: () => { if (!recognizing && capture.phase === "idle") { setNotice(null); setRetryable(false); setLimit(null); recording.current = null; void capture.start(); } },
    stop: capture.stop, cancel,
    retry: () => { if (recording.current && !recognizing) void transcribe(recording.current); },
  };
}
