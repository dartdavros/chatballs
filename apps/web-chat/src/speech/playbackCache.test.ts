import { describe, expect, it, vi } from "vitest";
import { PlaybackCache } from "./playbackCache";

describe("widget playback memory", () => {
  it("joins concurrent synthesis and reuses the same object URL on repeat", async () => {
    const cache = new PlaybackCache();
    let complete!: (blob: Blob) => void;
    const synthesize = vi.fn(() => new Promise<Blob>(resolve => { complete = resolve; }));
    const first = cache.get("session/message/text/revision", synthesize);
    expect(cache.get("session/message/text/revision", synthesize)).toBe(first);
    complete(new Blob(["audio"]));
    const url = await first;
    expect(await cache.get("session/message/text/revision", synthesize)).toBe(url);
    expect(synthesize).toHaveBeenCalledTimes(1);
    const revoke = vi.spyOn(URL, "revokeObjectURL");
    cache.clear();
    expect(revoke).toHaveBeenCalledWith(url);
    revoke.mockRestore();
  });

  it("discards stale flights on reset/unmount and can retry failed synthesis", async () => {
    const cache = new PlaybackCache();
    let complete!: (blob: Blob) => void;
    let signal!: AbortSignal;
    const flight = cache.get("old", current => { signal = current; return new Promise(resolve => { complete = resolve; }); });
    cache.clear();
    expect(signal.aborted).toBe(true);
    complete(new Blob(["stale"]));
    await expect(flight).rejects.toMatchObject({ name: "AbortError" });
    await expect(cache.get("retry", () => Promise.reject(new Error("failed")))).rejects.toThrow("failed");
    expect(await cache.get("retry", () => Promise.resolve(new Blob(["complete"])))).toMatch(/^blob:/);
    cache.clear();
  });

  it("separates session, message, text and configuration revisions", async () => {
    const cache = new PlaybackCache();
    const keys = [["s1", 1, "a", "r1"], ["s2", 1, "a", "r1"], ["s1", 2, "a", "r1"], ["s1", 1, "b", "r1"], ["s1", 1, "a", "r2"]];
    const urls = await Promise.all(keys.map(key => cache.get(JSON.stringify(key), () => Promise.resolve(new Blob(["audio"])) )));
    expect(new Set(urls).size).toBe(5);
    cache.clear();
  });
});
