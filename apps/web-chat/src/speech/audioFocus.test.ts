import { describe, expect, it, vi } from "vitest";
import { beginRecording, endRecording, focusAudio, onAudioInterrupt, releaseAudio } from "./audioFocus";

describe("recording and playback exclusion", () => {
  it("stops the first answer when another audio takes focus", () => {
    const first = { pause: vi.fn() } as unknown as HTMLAudioElement;
    const second = { pause: vi.fn() } as unknown as HTMLAudioElement;
    const interrupted = vi.fn();
    const unsubscribe = onAudioInterrupt(interrupted);
    expect(focusAudio(first)).toBe(true);
    expect(focusAudio(second)).toBe(true);
    expect(first.pause).toHaveBeenCalledOnce();
    expect(interrupted).toHaveBeenLastCalledWith(second);
    releaseAudio(second);
    unsubscribe();
  });

  it("recording interrupts pending playback and prevents audio focus until it ends", () => {
    const audio = { pause: vi.fn() } as unknown as HTMLAudioElement;
    const interrupted = vi.fn();
    const unsubscribe = onAudioInterrupt(interrupted);
    focusAudio(audio);
    beginRecording();
    expect(interrupted).toHaveBeenLastCalledWith(null);
    expect(audio.pause).toHaveBeenCalledOnce();
    expect(focusAudio(audio)).toBe(false);
    endRecording();
    expect(focusAudio(audio)).toBe(true);
    releaseAudio(audio);
    unsubscribe();
  });
});
