/** Widget-owned memory only. Disposal aborts flights and revokes every URL. */
export class PlaybackCache {
  private entries = new Map<string, { controller: AbortController; promise: Promise<string>; url?: string }>();

  get(key: string, synthesize: (signal: AbortSignal) => Promise<Blob>): Promise<string> {
    const existing = this.entries.get(key);
    if (existing) return existing.promise;
    const controller = new AbortController();
    const entry = { controller, promise: Promise.resolve(""), url: undefined as string | undefined };
    entry.promise = synthesize(controller.signal).then(blob => {
      if (controller.signal.aborted) throw new DOMException("Aborted", "AbortError");
      entry.url = URL.createObjectURL(blob);
      return entry.url;
    }).catch(error => {
      if (this.entries.get(key) === entry) this.entries.delete(key);
      throw error;
    });
    this.entries.set(key, entry);
    return entry.promise;
  }

  clear() {
    for (const entry of this.entries.values()) {
      entry.controller.abort();
      if (entry.url) URL.revokeObjectURL(entry.url);
    }
    this.entries.clear();
  }
}
