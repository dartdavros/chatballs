import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("webWidgetSnippet", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds the embed snippet from the current origin and channel code", async () => {
    vi.stubGlobal("window", { location: { origin: "https://hub.example.com" } });
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("wgt_edeves")).toBe(
      `<script src="https://hub.example.com/chat-widget.js" data-widget-key="wgt_edeves" async></script>`,
    );
  });

  it("follows whatever origin serves the page (one image, any domain)", async () => {
    vi.stubGlobal("window", { location: { origin: "https://acme.test" } });
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("wgt_foxray")).toBe(
      `<script src="https://acme.test/chat-widget.js" data-widget-key="wgt_foxray" async></script>`,
    );
  });

  it("uses the origin verbatim with a custom port", async () => {
    vi.stubGlobal("window", { location: { origin: "https://hub.example.com:8443" } });
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("wgt_edeves")).toBe(
      `<script src="https://hub.example.com:8443/chat-widget.js" data-widget-key="wgt_edeves" async></script>`,
    );
  });
});

// Гарантия отсутствия build-time привязки: сниппет выводится от текущего origin в
// рантайме, поэтому один frontend-образ работает на любом домене без пересборки
// (ADR-HUB-0028 §10).
