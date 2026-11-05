import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SiteEventMemory, validEvent } from "./memory";

// The dev widget container mounts only its app; pass the real checkout source
// there. A complete checkout (including CI) reads the same module directly.
const source = process.env.CHATBALLS_SITE_LOADER_BASE64
  ? Buffer.from(process.env.CHATBALLS_SITE_LOADER_BASE64, "base64").toString("utf8")
  : readFileSync(new URL("../../../backend/chatballs/webchat/loader_assets/site_events.js", import.meta.url), "utf8");
const event = (eventId, widgetKey = "widget-one") => ({ widgetKey, name: "checkout.help", eventId, data: { category: "private" } });

function mount(early = [], receive = () => {}) {
  const postMessage = vi.fn(receive);
  const fields = [{ name: "name", value: "unchanged" }];
  const api = { q: fields, eventQueue: early };
  const context = {
    window: { Chatballs: api, setTimeout, clearTimeout }, TextEncoder, Date,
    widgetKey: "widget-one", instanceId: "instance-one", origin: "https://widget.example",
    frame: { contentWindow: { postMessage } }, renderSiteInvitation: vi.fn(), setOpen: vi.fn(),
  };
  const controls = runInNewContext(`${source}\n({ handleSiteEventMessage, notifySiteEvent });`, context);
  return { api: context.window.Chatballs, controls, postMessage, fields };
}

describe("the real site loader queue", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(new Date("2026-11-05T12:00:00Z")); });
  afterEach(() => vi.useRealTimers());

  it("keeps the first matching early event apart from fields and waits for the matching instance", () => {
    const memory = new SiteEventMemory("marker", { getItem: () => null, setItem: vi.fn() });
    const rule = { name: "checkout.help", invitation: "Help?", schema: [{ name: "category", type: "string", maxLength: 120, required: true }] };
    const { api, controls, postMessage, fields } = mount([
      { event: { ...event("wrong-name"), name: "other.event" }, receivedAt: Date.now() },
      { event: { ...event("wrong-schema"), data: { category: null } }, receivedAt: Date.now() },
      { event: event("first"), receivedAt: Date.now() },
      { event: event("later"), receivedAt: Date.now() },
    ], packet => { if (validEvent(packet.event, rule, "widget-one")) memory.receive(packet.event, packet.receivedAt, false); });
    expect(api.q).toBe(fields);
    expect(api.eventQueue).toEqual([]);
    expect(postMessage).not.toHaveBeenCalled();
    controls.handleSiteEventMessage({ type: "chatballs-site-events-ready", widgetKey: "other", instanceId: "instance-one" });
    controls.handleSiteEventMessage({ type: "chatballs-site-events-ready", widgetKey: "widget-one", instanceId: "foreign" });
    expect(postMessage).not.toHaveBeenCalled();
    controls.handleSiteEventMessage({ type: "chatballs-site-events-ready", widgetKey: "widget-one", instanceId: "instance-one" });
    expect(postMessage).toHaveBeenCalledTimes(4);
    expect(postMessage).toHaveBeenNthCalledWith(3, expect.objectContaining({
      type: "chatballs-site-event", instanceId: "instance-one", widgetKey: "widget-one", event: event("first"),
    }), "https://widget.example");
    expect(memory.pending.event.eventId).toBe("first");
  });

  it("bounds pre-ready candidates and clears the original stub array", () => {
    const early = [{ event: event("early"), receivedAt: Date.now() }];
    const { api } = mount(early);
    expect(early).toEqual([]);
    for (let index = 0; index < 99; index += 1) expect(api.emitEvent(event(String(index)))).toBe(true);
    expect(api.emitEvent(event("overflow"))).toBe(false);
  });

  it("expires queued payloads from their original call time, including other widgets", () => {
    const { api, controls, postMessage } = mount([{ event: event("old"), receivedAt: Date.now() - 299000 }]);
    api.emitEvent(event("other", "widget-two"));
    vi.advanceTimersByTime(1001);
    controls.handleSiteEventMessage({ type: "chatballs-site-events-ready", widgetKey: "widget-one", instanceId: "instance-one" });
    expect(postMessage).not.toHaveBeenCalled();
    vi.advanceTimersByTime(300000);
    expect(api.__siteEvents.pending["widget-two"]).toBeUndefined();
  });

  it("routes post-load events separately and rejects oversized or invalid envelopes", () => {
    const { api, controls, postMessage } = mount();
    controls.handleSiteEventMessage({ type: "chatballs-site-events-ready", widgetKey: "widget-one", instanceId: "instance-one" });
    expect(api.emitEvent(event("other", "widget-two"))).toBe(true);
    expect(postMessage).not.toHaveBeenCalled();
    expect(api.emitEvent({ ...event(""), data: {} })).toBe(false);
    expect(api.emitEvent({ ...event("large"), data: { category: "я".repeat(11000) } })).toBe(false);
    expect(api.emitEvent(event("after"))).toBe(true);
    expect(postMessage).toHaveBeenCalledTimes(1);
    expect(postMessage.mock.calls[0][0].event.eventId).toBe("after");
  });
});
