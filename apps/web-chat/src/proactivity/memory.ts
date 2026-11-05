import type { PublicSiteEventRule, SiteEvent } from "@chatballs/contracts";

export const SITE_EVENT_TTL = 5 * 60 * 1000;
export type PendingSiteEvent = { event: SiteEvent; receivedAt: number; accepted: boolean };

export function validEvent(event: SiteEvent, rule: PublicSiteEventRule, widgetKey: string): boolean {
  if (!event || event.widgetKey !== widgetKey || event.name !== rule.name
    || typeof event.eventId !== "string" || !event.eventId.trim() || event.eventId.length > 200
    || !event.data || typeof event.data !== "object" || Array.isArray(event.data)) return false;
  try {
    const { name, eventId, data } = event;
    if (new TextEncoder().encode(JSON.stringify({ name, eventId, data })).length > 20 * 1024) return false;
    if (Object.keys(data).some((key) => !rule.schema.some((field) => field.name === key))) return false;
    return rule.schema.every((field) => {
      if (!Object.prototype.hasOwnProperty.call(data, field.name)) return !field.required;
      const value = data[field.name];
      if (field.type === "string") return typeof value === "string" && value.length <= field.maxLength;
      if (field.type === "number") return typeof value === "number" && Number.isFinite(value) && value >= field.minimum && value <= field.maximum;
      return typeof value === "boolean";
    });
  } catch { return false; }
}

/** Only a technical marker is serialized. Payload is deliberately memory-only. */
export class SiteEventMemory {
  pending: PendingSiteEvent | null = null;
  private seen = false;
  private restored = false;
  private stopped = false;
  constructor(private markerKey: string, private storage: Pick<Storage, "getItem" | "setItem">) {
    try { this.seen = storage.getItem(markerKey) === "1"; } catch { /* memory still enforces this page */ }
    this.restored = this.seen;
  }
  receive(event: SiteEvent, receivedAt: number, consent: boolean, now = Date.now()): boolean {
    if (this.pending || this.restored || this.stopped || (!consent && this.seen) || receivedAt > now || now - receivedAt >= SITE_EVENT_TTL) return false;
    this.seen = true;
    try { this.storage.setItem(this.markerKey, "1"); } catch { /* no payload fallback */ }
    this.pending = { event, receivedAt, accepted: consent };
    return true;
  }
  accept(now = Date.now()): boolean {
    if (this.expire(now) || !this.pending) return false;
    this.pending.accepted = true;
    return true;
  }
  expire(now = Date.now()): boolean {
    if (!this.pending || now - this.pending.receivedAt < SITE_EVENT_TTL) return false;
    this.stopped = true;
    this.clear();
    return true;
  }
  clear() { this.pending = null; }
}
