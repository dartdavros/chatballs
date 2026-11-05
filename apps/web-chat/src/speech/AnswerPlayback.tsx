import { useLayoutEffect, useRef, useState } from "react";
import { Loader, voiceWaveHeights } from "@chatballs/ui";
import { t } from "../i18n";
import { SpeechIcon } from "./SpeechIcon";
import type { AnswerPlaybackControl, PlaybackState } from "./useAnswerPlayback";

function Player({ state, toggle }: { state: PlaybackState; toggle: () => void }) {
  const wave = useRef<HTMLSpanElement>(null);
  const [bars, setBars] = useState(32);
  useLayoutEffect(() => {
    const measure = () => setBars(Math.min(32, Math.max(8, Math.floor(((wave.current?.clientWidth ?? 160) + 2) / 5))));
    measure();
    const observer = new ResizeObserver(measure);
    if (wave.current) observer.observe(wave.current);
    return () => observer.disconnect();
  }, []);
  const { phase, seconds } = state;
  const loading = phase === "loading", error = phase === "error", ended = phase === "ended";
  const label = loading ? "loadingAudio" : phase === "playing" ? "pause" : phase === "paused" ? "resume" : ended ? "replay" : "retry";
  const caption = error ? state.error ?? "ttsFailure" : loading ? "loadingAudio" : phase === "playing" ? "playing" : phase === "paused" ? "paused" : "ended";
  const time = `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  return <div className="voice-message wc-answer-player" data-player-state={phase}>
    <div className="voice-message-player">
      <button type="button" className="voice-message-play" onClick={toggle} disabled={loading} aria-label={t(`speech.${label}`)} title={t(`speech.${label}`)}>
        {loading ? <Loader size={20} /> : <SpeechIcon size={14} name={error || ended ? "refresh" : phase === "playing" ? "pause" : "play"} />}
      </button>
      <span ref={wave} className="voice-message-wave" aria-hidden="true">{voiceWaveHeights(state.messageId, bars).map((height, index) =>
        <i key={index} style={{ height }} className={index < Math.round(state.progress * bars) ? "is-played" : ""} />)}</span>
      <em>{loading || error ? "—:—" : time}</em>
    </div>
    <div className={`wc-player-status ${error ? "voice-message-error" : ""}`} role="status" aria-live="polite"><span>{t(`speech.${caption}`)}</span></div>
  </div>;
}

export function AnswerPlayback({ control, messageId, text }: { control: AnswerPlaybackControl; messageId: number; text: string }) {
  const surface = useRef<HTMLDivElement>(null);
  const state = control.state?.messageId === messageId ? control.state : null;
  const expanded = state !== null;
  useLayoutEffect(() => {
    if (expanded) surface.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [expanded]);
  const label = t(state ? "speech.stop" : "speech.listen");
  return <div ref={surface} className="wc-answer-audio">
    {state && <Player state={state} toggle={control.toggle} />}
    <button type="button" className="wc-icon-button cb-composer-button wc-answer-audio-toggle" aria-expanded={Boolean(state)}
      aria-label={label} title={label} onClick={() => state ? control.stop() : control.start(messageId, text)}><SpeechIcon size={16} name={state ? "stop" : "sound"} /></button>
  </div>;
}
