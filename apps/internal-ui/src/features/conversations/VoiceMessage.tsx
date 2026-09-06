import { useEffect, useRef, useState } from "react";

import { Icon } from "../../shared/icons";
import { resolveApiUrl } from "../../api/client";
import { transcribeMessage, type ApiMessage } from "./model";

// Голосовое сообщение в ленте (дизайн-базлайн v2, кадр H): плеер с волной,
// длительность и расшифровка по кнопке (три состояния).

export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// Детерминированная волна из id: реальная амплитуда не хранится, рисунок
// стабилен между рендерами (как в макете).
function waveHeights(seed: number, bars = 32): number[] {
  const heights: number[] = [];
  let value = seed || 1;
  for (let index = 0; index < bars; index += 1) {
    value = (value * 1103515245 + 12345) % 2147483648;
    heights.push(4 + (value % 17));
  }
  return heights;
}

export function VoiceMessage({ message: incoming }: { message: ApiMessage }) {
  // Локальная копия: расшифровка приходит из POST-ответа сразу, а фоновый
  // поллинг detail затем подтверждает её с сервера.
  const [message, setMessage] = useState(incoming);
  useEffect(() => {
    setMessage(incoming);
  }, [incoming.id, incoming.transcriptStatus, incoming.transcript]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [transcribing, setTranscribing] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true);
  const [errorText, setErrorText] = useState("");
  const bars = waveHeights(message.id);

  useEffect(() => () => {
    audioRef.current?.pause();
  }, []);

  function toggle() {
    if (!message.audioUrl) return;
    if (!audioRef.current) {
      const audio = new Audio(resolveApiUrl(message.audioUrl));
      audio.addEventListener("timeupdate", () => {
        if (audio.duration) setProgress(audio.currentTime / audio.duration);
      });
      audio.addEventListener("ended", () => {
        setPlaying(false);
        setProgress(0);
      });
      audioRef.current = audio;
    }
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
    } else {
      void audioRef.current.play().catch(() => setErrorText("Не удалось воспроизвести"));
      setPlaying(true);
    }
  }

  async function transcribe() {
    setTranscribing(true);
    setErrorText("");
    try {
      setMessage(await transcribeMessage(message.id));
      setShowTranscript(true);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось расшифровать");
    } finally {
      setTranscribing(false);
    }
  }

  const played = Math.round(progress * bars.length);

  return (
    <div className="voice-message">
      <div className="voice-message-player">
        <button
          aria-label={playing ? "Пауза" : "Воспроизвести"}
          className="voice-message-play"
          disabled={!message.audioUrl}
          type="button"
          onClick={toggle}
        >
          <Icon name={playing ? "pause" : "play"} size={14} />
        </button>
        <span className="voice-message-wave">
          {bars.map((height, index) => (
            <i className={index < played ? "is-played" : ""} key={index} style={{ height }} />
          ))}
        </span>
        {message.transcriptStatus !== "READY" && !transcribing && message.audioUrl && (
          <button
            className="voice-message-transcribe"
            title="Расшифровать"
            type="button"
            onClick={() => void transcribe()}
          >
            <Icon name="text" size={13} />Расшифровать
          </button>
        )}
        {transcribing && <span className="voice-message-busy" title="Расшифровываем…"><i /><i /><i /><em>Расшифровываем…</em></span>}
        <em>{formatDuration(message.durationSeconds ?? 0)}</em>
      </div>
      {message.transcriptStatus === "READY" && message.transcript && showTranscript && (
        <p className="voice-message-transcript">
          {message.transcript}
          <span className="voice-message-caption">Расшифровка AI · <button className="link" type="button" onClick={() => setShowTranscript(false)}>Скрыть</button></span>
        </p>
      )}
      {message.transcriptStatus === "READY" && !showTranscript && (
        <span className="voice-message-caption voice-message-show">Расшифровка AI · <button className="link" type="button" onClick={() => setShowTranscript(true)}>Показать</button></span>
      )}
      {errorText && <p className="voice-message-error">{errorText}</p>}
    </div>
  );
}
