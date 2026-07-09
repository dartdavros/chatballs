import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./client";

function jsonResponse(body: unknown, init: { status?: number; ok?: boolean } = {}): Response {
  const status = init.status ?? 200;
  return {
    ok: init.ok ?? true,
    status,
    json: async () => body,
  } as unknown as Response;
}

function emptyResponse(status: number): Response {
  return { ok: true, status, json: async () => { throw new SyntaxError("Unexpected end of JSON input"); } } as unknown as Response;
}

const originalFetch = globalThis.fetch;
const originalDocumentCookie = (globalThis as { document?: { cookie?: string } }).document?.cookie;

afterEach(() => {
  globalThis.fetch = originalFetch;
  if (originalDocumentCookie === undefined) {
    delete (globalThis as { document?: { cookie?: string } }).document;
  }
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("resolves 204 No Content to undefined without parsing the body", async () => {
    (globalThis as { document?: { cookie?: string } }).document = { cookie: "csrftoken=abc" };
    globalThis.fetch = vi.fn().mockResolvedValue(emptyResponse(204)) as unknown as typeof fetch;

    await expect(api("/api/v1/integrations/1/", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("resolves 205 Reset Content to undefined", async () => {
    (globalThis as { document?: { cookie?: string } }).document = { cookie: "csrftoken=abc" };
    globalThis.fetch = vi.fn().mockResolvedValue(emptyResponse(205)) as unknown as typeof fetch;

    await expect(api("/api/v1/items/1/", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("parses JSON for a normal 200 response", async () => {
    const payload = { integration: { id: 5 } };
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(payload)) as unknown as typeof fetch;

    await expect(api("/api/v1/integrations/")).resolves.toEqual(payload);
  });

  it("throws with the server detail on an error response", async () => {
    const payload = { detail: "Интеграция не найдена" };
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(payload, { status: 404, ok: false })) as unknown as typeof fetch;

    await expect(api("/api/v1/integrations/1/")).rejects.toThrow("Интеграция не найдена");
  });
});
