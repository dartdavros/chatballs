import { useEffect, useRef, useState } from "react";
import { focusAudio, onAudioInterrupt, releaseAudio } from "./audioFocus";
import { PlaybackCache } from "./playbackCache";
import { synthesizeAnswer, SynthesisError } from "./synthesisApi";

export type PlaybackState = { messageId: number; phase: "loading" | "playing" | "paused" | "ended" | "error"; progress: number; seconds: number; error?: "playbackFailure" | "voiceUnavailable" | "languageUnavailable" | "ttsFailure" };
export type AnswerPlaybackControl = {
  state: PlaybackState | null;
  start: (messageId: number, text: string) => void;
  toggle: () => void;
  stop: () => void;
};

export function useAnswerPlayback(token: string | null, revision: string, hostOrigin: string) {
  const cache = useRef(new PlaybackCache());
  const audio = useRef<HTMLAudioElement | null>(null);
  const attempt = useRef(0);
  const [state, setState] = useState<PlaybackState | null>(null);
  const request = useRef<{ messageId: number; text: string } | null>(null);

  function stop() {
    attempt.current++;
    const current = audio.current;
    audio.current = null;
    if (current) {
      current.onpause = current.onended = current.onerror = current.ontimeupdate = null;
      current.pause(); current.removeAttribute("src"); current.load(); releaseAudio(current);
    }
    request.current = null;
    setState(null);
  }

  function clear() { stop(); cache.current.clear(); }

  useEffect(() => { clear(); return clear; }, [token, revision]);
  useEffect(() => onAudioInterrupt(other => { if (other !== audio.current || !other) stop(); }), []);

  async function play(current: HTMLAudioElement, id: number) {
    if (!focusAudio(current)) { stop(); return; }
    try {
      await current.play();
      if (attempt.current === id) setState(value => value && { ...value, phase: "playing", error: undefined });
    } catch {
      if (attempt.current === id) setState(value => value && { ...value, phase: "error", error: "playbackFailure" });
    }
  }

  async function start(messageId: number, text: string) {
    if (!token || !revision) return;
    // Repeated clicks on the same flight join it, without resetting its UI.
    if (request.current?.messageId === messageId && state?.phase === "loading") return;
    stop();
    const id = attempt.current;
    request.current = { messageId, text };
    setState({ messageId, phase: "loading", progress: 0, seconds: 0 });
    try {
      const key = JSON.stringify([token, messageId, text, revision]);
      const url = await cache.current.get(key, signal => synthesizeAnswer(token, messageId, revision, hostOrigin, signal));
      if (attempt.current !== id) return;
      const current = new Audio(url);
      audio.current = current;
      current.ontimeupdate = () => setState(value => attempt.current === id && value
        ? { ...value, progress: current.duration ? current.currentTime / current.duration : 0, seconds: current.currentTime } : value);
      current.onpause = () => setState(value => attempt.current === id && value && value.phase === "playing" ? { ...value, phase: "paused" } : value);
      current.onended = () => setState(value => attempt.current === id && value ? { ...value, phase: "ended", progress: 1, seconds: current.duration } : value);
      current.onerror = () => setState(value => attempt.current === id && value ? { ...value, phase: "error", error: "playbackFailure" } : value);
      await play(current, id);
    } catch (error) {
      if (attempt.current !== id) return;
      const code = error instanceof SynthesisError ? error.code : "";
      const notice = code === "voice_unavailable" ? "voiceUnavailable" : code === "voice_language_unsupported" ? "languageUnavailable" : "ttsFailure";
      setState({ messageId, phase: "error", progress: 0, seconds: 0, error: notice });
    }
  }

  function toggle() {
    const current = audio.current;
    if (state?.phase === "loading") return;
    if (state?.phase === "error" || !current) {
      if (request.current) void start(request.current.messageId, request.current.text);
    } else if (!current.paused) current.pause();
    else {
      if (state?.phase === "ended") current.currentTime = 0;
      void play(current, attempt.current);
    }
  }
  return { state, start: (messageId: number, text: string) => void start(messageId, text), toggle, stop, clear };
}
