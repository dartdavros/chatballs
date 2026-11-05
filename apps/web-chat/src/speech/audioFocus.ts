let active: HTMLAudioElement | null = null;
let recording = false;

export function beginRecording() {
  recording = true;
  active?.pause();
  active = null;
}

export function endRecording() { recording = false; }

export function focusAudio(audio: HTMLAudioElement): boolean {
  if (recording) return false;
  if (active !== audio) active?.pause();
  active = audio;
  return true;
}
