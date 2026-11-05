import { afterEach, describe, expect, it, vi } from "vitest";
import { AudioCapture } from "./capture";

// Native media unit doubles only; no API/server or application data is replaced.
class Recorder extends EventTarget {
  static isTypeSupported() { return true; }
  static instances: Recorder[] = [];
  state = "inactive";
  mimeType = "audio/webm";
  constructor(readonly stream: MediaStream) { super(); Recorder.instances.push(this); }
  start() { this.state = "recording"; }
  stop() { this.state = "inactive"; }
}

function setup() {
  vi.useFakeTimers();
  Recorder.instances = [];
  const stopTrack = vi.fn();
  const stream = { getTracks: () => [{ stop: stopTrack }] } as unknown as MediaStream;
  const acquire = vi.fn<() => Promise<MediaStream>>();
  vi.stubGlobal("MediaRecorder", Recorder);
  vi.stubGlobal("navigator", { mediaDevices: { getUserMedia: acquire } });
  const events = { phase: vi.fn(), tick: vi.fn(), complete: vi.fn(), error: vi.fn() };
  const capture = new AudioCapture(events, 10485760, 60);
  return { capture, events, stream, acquire, stopTrack };
}

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe("closing audio capture", () => {
  it("discards a late microphone grant and permits reopening", async () => {
    const { capture, events, stream, acquire, stopTrack } = setup();
    let grant!: (stream: MediaStream) => void;
    acquire.mockImplementationOnce(() => new Promise(resolve => { grant = resolve; }));
    const pending = capture.start();
    expect(events.phase).toHaveBeenLastCalledWith("permission");
    capture.cancel();
    expect(events.phase).toHaveBeenLastCalledWith("idle");
    grant(stream); await pending;
    expect(stopTrack).toHaveBeenCalledOnce();
    expect(Recorder.instances).toHaveLength(0);
    expect(events.complete).not.toHaveBeenCalled();
    acquire.mockResolvedValue(stream);
    await capture.start();
    expect(events.phase).toHaveBeenLastCalledWith("recording");
    capture.cancel();
  });

  it("releases recording tracks and timers and ignores old events after reopening", async () => {
    const { capture, events, stream, acquire, stopTrack } = setup();
    acquire.mockResolvedValue(stream);
    await capture.start();
    const first = Recorder.instances[0];
    capture.cancel();
    expect(first.state).toBe("inactive");
    expect(stopTrack).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
    await capture.start();
    first.dispatchEvent(new Event("stop"));
    first.dispatchEvent(new Event("error"));
    expect(events.phase).toHaveBeenLastCalledWith("recording");
    expect(events.complete).not.toHaveBeenCalled();
    expect(events.error).not.toHaveBeenCalled();
    capture.cancel();
  });
});
