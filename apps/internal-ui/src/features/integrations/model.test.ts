import { beforeEach, describe, expect, it, vi } from "vitest";

describe("webWidgetSnippet", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("builds the embed snippet from the public hub url and channel code", async () => {
    vi.stubEnv("VITE_PUBLIC_HUB_URL", "https://hub.edevs.tech");
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("edeves")).toBe(
      `<script src="https://hub.edevs.tech/chat-widget.js" data-channel="edeves" async></script>`,
    );
  });

  it("strips trailing slashes from the hub url", async () => {
    vi.stubEnv("VITE_PUBLIC_HUB_URL", "https://hub.edevs.tech/");
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("foxray")).toBe(
      `<script src="https://hub.edevs.tech/chat-widget.js" data-channel="foxray" async></script>`,
    );
  });

  it("falls back to a relative src when the hub url is empty", async () => {
    vi.stubEnv("VITE_PUBLIC_HUB_URL", "");
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("edeves")).toBe(
      `<script src="/chat-widget.js" data-channel="edeves" async></script>`,
    );
  });
});
