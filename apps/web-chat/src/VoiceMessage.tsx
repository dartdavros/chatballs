import { useEffect, useRef, useState } from "react";

import { voiceWaveHeights } from "@chatballs/ui";

import { t } from "./i18n";
import { focusAudio } from "./speech/audioFocus";

// Голосовое сообщение в виджете: тот же плеер, что видит оператор в своём чате
// (дизайн-базлайн v2, кадр H) — кнопка воспроизведения, волна и длительность.
// Расшифровки здесь нет: это инструмент оператора, клиент слушает свою же
// запись и в пересказе не нуждается.

function formatSeconds(total: number): string {
  const seconds = Math.max(0, Math.round(total));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

const PLAY_ICON = <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" stroke="none"><polygon points="7 4 20 12 7 20" /></svg>;
const PAUSE_ICON = <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" stroke="none"><rect x="7" y="4" width="3.6" height="16" rx="1" /><rect x="13.4" y="4" width="3.6" height="16" rx="1" /></svg>;

export function VoiceMessage({ messageId, url, durationSeconds, accent, light }: {
  messageId: number;
  url: string;
  durationSeconds?: number;
  accent: string;
  /** Пузырь клиента — на акцентной заливке; плеер на ней рисуется белым. */
  light: boolean;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [failed, setFailed] = useState(false);
  const bars = voiceWaveHeights(messageId);
  const played = Math.round(progress * bars.length);

  useEffect(() => () => {
    audioRef.current?.pause();
  }, []);

  function toggle() {
    if (!audioRef.current) {
      const audio = new Audio(url);
      audio.addEventListener("timeupdate", () => {
        if (audio.duration) setProgress(audio.currentTime / audio.duration);
      });
      audio.addEventListener("ended", () => {
        setPlaying(false);
        setProgress(0);
      });
      audioRef.current = audio;
      audio.addEventListener("pause", () => setPlaying(false));
    }
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }
    if (!focusAudio(audioRef.current)) return;
    void audioRef.current.play().catch(() => {
      setFailed(true);
      setPlaying(false);
    });
    setPlaying(true);
  }

  const idle = light ? "rgba(255,255,255,0.45)" : "#d9d9d9";
  const done = light ? "#ffffff" : accent;
  return (
    <div style={{ minWidth: 216 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          onClick={toggle}
          aria-label={playing ? t("chat.pause") : t("chat.play")}
          style={{
            width: 34,
            height: 34,
            flex: "none",
            border: "none",
            borderRadius: "50%",
            background: light ? "rgba(255,255,255,0.22)" : accent,
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
          }}
        >
          {playing ? PAUSE_ICON : PLAY_ICON}
        </button>
        <span style={{ flex: 1, display: "flex", alignItems: "center", gap: 2, height: 24, minWidth: 110 }}>
          {bars.map((height, index) => (
            <i
              key={index}
              style={{
                display: "block",
                width: 3,
                height,
                flex: "none",
                borderRadius: 1.5,
                background: index < played ? done : idle,
              }}
            />
          ))}
        </span>
        <span style={{
          flex: "none",
          fontSize: 12,
          fontWeight: 500,
          fontVariantNumeric: "tabular-nums",
          color: light ? "rgba(255,255,255,0.8)" : "#8c8c8c",
        }}>{formatSeconds(durationSeconds ?? 0)}</span>
      </div>
      {failed && (
        <div style={{ marginTop: 6, fontSize: 11.5, color: light ? "rgba(255,255,255,0.9)" : "#cf1322" }}>
          {t("chat.could_not_play")}
        </div>
      )}
    </div>
  );
}
