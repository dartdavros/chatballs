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

    expect(webWidgetSnippet("wgt_demo")).toBe(
      `<script src="https://hub.example.com/chat-widget.js" data-widget-key="wgt_demo" async></script>`,
    );
  });

  it("follows whatever origin serves the page (one image, any domain)", async () => {
    vi.stubGlobal("window", { location: { origin: "https://acme.test" } });
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("wgt_acme")).toBe(
      `<script src="https://acme.test/chat-widget.js" data-widget-key="wgt_acme" async></script>`,
    );
  });

  it("uses the origin verbatim with a custom port", async () => {
    vi.stubGlobal("window", { location: { origin: "https://hub.example.com:8443" } });
    const { webWidgetSnippet } = await import("./model");

    expect(webWidgetSnippet("wgt_demo")).toBe(
      `<script src="https://hub.example.com:8443/chat-widget.js" data-widget-key="wgt_demo" async></script>`,
    );
  });
});

describe("parseAllowedOrigins", () => {
  it("splits on commas, semicolons and newlines and trims each entry", async () => {
    const { parseAllowedOrigins } = await import("./model");

    expect(parseAllowedOrigins(` example.com ,
*.example.com; shop.example `)).toEqual([
      "example.com",
      "*.example.com",
      "shop.example",
    ]);
  });

  it("drops empty entries, trailing slashes and case-insensitive duplicates", async () => {
    const { parseAllowedOrigins } = await import("./model");

    expect(parseAllowedOrigins("example.com/, ,, EXAMPLE.COM, example.com")).toEqual(["example.com"]);
  });

  it("returns an empty list for blank input so the form can require a domain", async () => {
    const { parseAllowedOrigins } = await import("./model");

    expect(parseAllowedOrigins(`
  `)).toEqual([]);
  });
});

describe("invalidAllowedOrigin", () => {
  it("accepts the three forms origin_allowed understands", async () => {
    const { invalidAllowedOrigin } = await import("./model");

    expect(
      invalidAllowedOrigin(["example.com", "*.example.com", "https://app.example.com", "localhost:5173"]),
    ).toBeUndefined();
  });

  it("reports the first entry that is not a domain", async () => {
    const { invalidAllowedOrigin } = await import("./model");

    expect(invalidAllowedOrigin(["example.com", "https://example.com/chat"])).toBe("https://example.com/chat");
    expect(invalidAllowedOrigin(["не домен"])).toBe("не домен");
  });
});

// Гарантия отсутствия build-time привязки: сниппет выводится от текущего origin в
// рантайме, поэтому один frontend-образ работает на любом домене без пересборки
// (ADR-HUB-0028 §10).
