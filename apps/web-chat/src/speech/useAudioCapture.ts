import { useEffect, useRef, useState } from "react";
import { AudioCapture, type CaptureLimit, type CapturePhase } from "./capture";

export function useAudioCapture({ maxBytes, maxSeconds, onComplete, onError }: {
  maxBytes: number; maxSeconds?: number;
  onComplete: (audio: Blob, seconds: number, limit: CaptureLimit) => void;
  onError: (kind: "unsupported" | "denied" | "formatError") => void;
}) {
  const [phase, setPhase] = useState<CapturePhase>("idle");
  const [seconds, setSeconds] = useState(0);
  const callbacks = useRef({ onComplete, onError });
  callbacks.current = { onComplete, onError };
  const engine = useRef<AudioCapture | null>(null);
  useEffect(() => {
    const capture = new AudioCapture({
      phase: setPhase, tick: setSeconds,
      complete: (...args) => callbacks.current.onComplete(...args),
      error: (kind) => callbacks.current.onError(kind),
    }, maxBytes, maxSeconds);
    engine.current = capture;
    return () => { capture.cancel(); engine.current = null; };
  }, [maxBytes, maxSeconds]);
  return {
    phase, seconds,
    start: () => engine.current?.start(),
    stop: () => engine.current?.stop(),
    cancel: () => engine.current?.cancel(),
  };
}
