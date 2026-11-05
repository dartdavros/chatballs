import { beginRecording, endRecording } from "./audioFocus";

export type CapturePhase = "idle" | "permission" | "recording";
export type CaptureLimit = "size" | "duration" | null;
type Events = {
  phase: (value: CapturePhase) => void;
  tick: (seconds: number) => void;
  complete: (audio: Blob, seconds: number, limit: CaptureLimit) => void;
  error: (kind: "unsupported" | "denied" | "formatError") => void;
};

function mimeType(): string {
  for (const candidate of ["audio/ogg;codecs=opus", "audio/webm;codecs=opus", "audio/mp4", "audio/webm"]) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return "";
}

export class AudioCapture {
  private recorder: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private interval: ReturnType<typeof setInterval> | null = null;
  private deadline: ReturnType<typeof setTimeout> | null = null;
  private generation = 0;
  private phase: CapturePhase = "idle";
  private limit: CaptureLimit = null;
  private started = 0;
  private bytes = 0;

  constructor(private events: Events, private maxBytes: number, private maxSeconds?: number) {}

  private setPhase(value: CapturePhase) { this.phase = value; this.events.phase(value); }

  private release(recorder: MediaRecorder | null) {
    recorder?.stream.getTracks().forEach((track) => track.stop());
    if (this.interval) clearInterval(this.interval);
    if (this.deadline) clearTimeout(this.deadline);
    this.interval = null;
    this.deadline = null;
    this.recorder = null;
    endRecording();
  }

  async start() {
    if (this.phase !== "idle") return;
    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      this.events.error("unsupported"); return;
    }
    const generation = ++this.generation;
    this.setPhase("permission");
    beginRecording();
    let stream: MediaStream | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (generation !== this.generation) { stream.getTracks().forEach((track) => track.stop()); return; }
      const type = mimeType();
      const recorder = new MediaRecorder(stream, { ...(type ? { mimeType: type } : {}), audioBitsPerSecond: 32000 });
      this.recorder = recorder;
      this.chunks = [];
      this.bytes = 0;
      this.limit = null;
      this.started = performance.now();
      recorder.addEventListener("dataavailable", (event) => {
        if (generation !== this.generation || !event.data.size) return;
        if (this.bytes + event.data.size <= this.maxBytes) {
          this.chunks.push(event.data);
          this.bytes += event.data.size;
        } else this.limit = "size";
        if (this.bytes >= this.maxBytes || this.limit === "size") this.stop("size");
      });
      recorder.addEventListener("error", () => {
        if (generation !== this.generation) return;
        this.cancel(); this.events.error("formatError");
      });
      recorder.addEventListener("stop", () => {
        if (generation !== this.generation) return;
        const seconds = (performance.now() - this.started) / 1000;
        const audio = new Blob(this.chunks, { type: recorder.mimeType || "audio/webm" });
        this.chunks = [];
        this.release(recorder);
        this.setPhase("idle");
        if (audio.size) this.events.complete(audio, seconds, this.limit);
        else this.events.error("formatError");
      });
      recorder.start(100);
      this.setPhase("recording");
      this.events.tick(0);
      this.interval = setInterval(() => this.events.tick(Math.floor((performance.now() - this.started) / 1000)), 200);
      if (this.maxSeconds) this.deadline = setTimeout(() => this.stop("duration"), this.maxSeconds * 1000);
    } catch {
      stream?.getTracks().forEach((track) => track.stop());
      if (generation !== this.generation) return;
      this.release(this.recorder);
      this.setPhase("idle"); this.events.error("denied");
    }
  }

  stop(limit: CaptureLimit = null) {
    this.limit = this.limit || limit;
    if (this.recorder?.state === "recording") this.recorder.stop();
  }

  cancel() {
    ++this.generation;
    if (this.recorder && this.recorder.state !== "inactive") this.recorder.stop();
    this.release(this.recorder);
    this.chunks = [];
    this.setPhase("idle");
  }
}
