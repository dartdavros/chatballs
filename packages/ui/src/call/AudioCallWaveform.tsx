// Живая осциллограмма аудиозвонка (baseline «Аудиозвонок.dc.html»).
// Белая линия rgba(255,255,255,.92), lineWidth 3, конусное затухание по краям.
// Амплитуда берётся из AnalyserNode удалённого потока — волна реагирует на
// голос собеседника. Нет потока/тишина → мягкая анимированная idle-волна.

import { useEffect, useRef } from "react";

type Props = {
  stream?: MediaStream | null;
  micOn?: boolean;
  active: boolean;
};

const IDLE_AMP = 0.12;
const SPEAK_AMP = 0.5;

export function AudioCallWaveform({ stream, micOn = true, active }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(stream);
  streamRef.current = stream;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = canvas.width;
    const H = canvas.height;
    const mid = H / 2;

    // AnalyserNode на удалённом аудио, чтобы измерять громкость собеседника.
    let audioCtx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let levels: Uint8Array<ArrayBuffer> | null = null;

    try {
      const target = streamRef.current;
      if (target && target.getAudioTracks().length > 0) {
        audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 1024;
        source = audioCtx.createMediaStreamSource(target);
        source.connect(analyser);
        levels = new Uint8Array(new ArrayBuffer(analyser.frequencyBinCount));
      }
    } catch {
      // AudioContext недоступен (нет аудио/нет прав) — работаем idle-волной.
    }

    let raf = 0;
    const draw = (ts: number) => {
      raf = requestAnimationFrame(draw);
      ctx.clearRect(0, 0, W, H);
      // Уровень громкости собеседника 0..1 (RMS по bins).
      let level = 0;
      if (active && micOn && analyser && levels) {
        analyser.getByteTimeDomainData(levels);
        let sum = 0;
        for (let i = 0; i < levels.length; i++) {
          const v = (levels[i] - 128) / 128;
          sum += v * v;
        }
        level = Math.min(1, Math.sqrt(sum / levels.length) * 2.4);
      }
      const speaking = active && micOn;
      const t = ts / 1000;
      const base = speaking ? SPEAK_AMP : IDLE_AMP;
      const ampScale = speaking ? (0.35 + 0.65 * level) : 1;

      ctx.lineWidth = 3;
      ctx.lineJoin = "round";
      ctx.strokeStyle = "rgba(255,255,255,0.92)";
      ctx.beginPath();
      for (let x = 0; x <= W; x += 4) {
        const p = x / W;
        const env = Math.sin(p * Math.PI); // taper ends
        const amp = env * H * 0.36 * base * ampScale * (0.6 + 0.4 * Math.sin(t * 2.1 + p * 3));
        const y = mid + Math.sin(p * 22 + t * 6) * amp + Math.sin(p * 9 - t * 3.3) * amp * 0.5;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      source?.disconnect();
      analyser?.disconnect();
      void audioCtx?.close();
    };
  }, [active, micOn]);

  return <canvas ref={canvasRef} width={520} height={112} className="hub-audio-wave" />;
}
