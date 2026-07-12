import { useCallback, useEffect, useRef } from "react";

function safelyPlay(audio: HTMLAudioElement) {
  void audio.play().catch(() => {
    // Браузер может запретить autoplay до первого действия пользователя.
  });
}

export function useAudioCue(src: string, volume = 1) {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => () => {
    audioRef.current?.pause();
    audioRef.current = null;
  }, []);

  return useCallback(() => {
    const audio = audioRef.current ?? new Audio(src);
    audioRef.current = audio;
    audio.volume = volume;
    audio.currentTime = 0;
    safelyPlay(audio);
  }, [src, volume]);
}

export function useLoopingAudio(src: string, active: boolean, volume = 1) {
  useEffect(() => {
    if (!active) return;
    const audio = new Audio(src);
    audio.loop = true;
    audio.volume = volume;
    safelyPlay(audio);
    return () => {
      audio.pause();
      audio.currentTime = 0;
    };
  }, [active, src, volume]);
}
