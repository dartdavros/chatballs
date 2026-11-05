import { describe, expect, it } from "vitest";
import type { PublicSiteEventRule, SiteEvent } from "@chatballs/contracts";
import { SiteEventMemory, SITE_EVENT_TTL, validEvent } from "./memory";

const rule: PublicSiteEventRule = { name: "checkout.help", invitation: "Help?",
  schema: [{ name: "category", type: "string", maxLength: 120, required: true }] };
const event: SiteEvent = { widgetKey: "widget-a", name: rule.name, eventId: "stable-id", data: { category: "private-value" } };
function markerStorage() {
  const values = new Map<string, string>();
  return { values, getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value); } };
}

describe("site event memory", () => {
  it("keeps the first event and writes only a technical marker", () => {
    const storage = markerStorage(), memory = new SiteEventMemory("origin:widget-a", storage);
    expect(memory.receive(event, 10, false, 10)).toBe(true);
    expect(memory.receive({ ...event, eventId: "second", data: { category: "second" } }, 11, false, 11)).toBe(false);
    expect(memory.pending?.event).toBe(event);
    expect([...storage.values]).toEqual([["origin:widget-a", "1"]]);
    expect(JSON.stringify([...storage.values])).not.toContain("private-value");
  });
  it("expires at five minutes and cannot launch after late consent", () => {
    const memory = new SiteEventMemory("origin:widget-a", markerStorage());
    memory.receive(event, 10, false, 10);
    expect(memory.accept(10 + SITE_EVENT_TTL)).toBe(false);
    expect(memory.pending).toBeNull();
    expect(memory.receive(event, 10 + SITE_EVENT_TTL + 1, true, 10 + SITE_EVENT_TTL + 1)).toBe(false);
  });
  it("reload loses data and preserves suppression even after consent elsewhere", () => {
    const storage = markerStorage();
    const first = new SiteEventMemory("origin:widget-a", storage);
    first.receive(event, 10, false, 10);
    first.clear();
    const reloaded = new SiteEventMemory("origin:widget-a", storage);
    expect(reloaded.pending).toBeNull();
    expect(reloaded.receive(event, 12, false, 12)).toBe(false);
    expect(reloaded.receive(event, 12, true, 12)).toBe(false);
    expect(new SiteEventMemory("origin:widget-b", storage).receive({ ...event, widgetKey: "widget-b" }, 12, false, 12)).toBe(true);
  });
  it("accepts an existing current consent and permits an explicit transport retry", () => {
    const memory = new SiteEventMemory("origin:widget-a", markerStorage());
    expect(memory.receive(event, 10, true, 10)).toBe(true);
    expect(memory.pending?.accepted).toBe(true);
    memory.clear();
    expect(memory.receive(event, 11, true, 11)).toBe(true);
  });
  it("validates routing and bounded typed data locally", () => {
    expect(validEvent(event, rule, "widget-a")).toBe(true);
    expect(validEvent(event, rule, "widget-b")).toBe(false);
    expect(validEvent({ ...event, data: { extra: "private-value" } }, rule, "widget-a")).toBe(false);
    expect(validEvent({ ...event, data: { category: "x".repeat(121) } }, rule, "widget-a")).toBe(false);
    expect(validEvent({ ...event, data: { category: false } }, rule, "widget-a")).toBe(false);
  });
});
