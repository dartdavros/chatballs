let active: HTMLAudioElement | null = null;
let recording = false;
const listeners = new Set<(audio: HTMLAudioElement | null) => void>();

export function onAudioInterrupt(listener: (audio: HTMLAudioElement | null) => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function beginRecording() {
  recording = true;
  listeners.forEach(listener => listener(null));
  active?.pause();
  active = null;
}

export function endRecording() { recording = false; }

export function releaseAudio(audio: HTMLAudioElement) {
  if (active === audio) active = null;
}

export function focusAudio(audio: HTMLAudioElement): boolean {
  if (recording) return false;
  listeners.forEach(listener => listener(audio));
  if (active !== audio) active?.pause();
  active = audio;
  return true;
}
