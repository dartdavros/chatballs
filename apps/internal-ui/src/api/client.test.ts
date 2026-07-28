import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, setActiveOrganization } from "./client";

const organizationPublicId = "123e4567-e89b-12d3-a456-426614174000";

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
  setActiveOrganization(null);
  globalThis.fetch = originalFetch;
  if (originalDocumentCookie === undefined) {
    delete (globalThis as { document?: { cookie?: string } }).document;
  }
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("resolves 204 No Content to undefined without parsing the body", async () => {
    setActiveOrganization(organizationPublicId);
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
    setActiveOrganization(organizationPublicId);
    const payload = { integration: { id: 5 } };
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(payload)) as unknown as typeof fetch;

    await expect(api("/api/v1/integrations/")).resolves.toEqual(payload);
  });

  it("throws with the server detail on an error response", async () => {
    setActiveOrganization(organizationPublicId);
    const payload = { detail: "Интеграция не найдена" };
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse(payload, { status: 404, ok: false })) as unknown as typeof fetch;

    await expect(api("/api/v1/integrations/1/")).rejects.toThrow("Интеграция не найдена");
  });

  it("preserves status and structured payload on an error response", async () => {
    setActiveOrganization(organizationPublicId);
    (globalThis as { document?: { cookie?: string } }).document = { cookie: "csrftoken=abc" };
    const payload = {
      code: "agent_knowledge_scope_conflict",
      detail: "Knowledge scope conflicts with assigned agents",
      conflicts: [{ agent: { id: 4, name: "Sales" }, knowledge: { id: 8, title: "Policy" } }],
    };
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse(payload, { status: 409, ok: false }),
    ) as unknown as typeof fetch;

    const error = await api("/api/v1/ai/knowledge/8/", { method: "PATCH", body: "{}" })
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, payload });
  });

  it("uses the canonical organization API route", async () => {
    setActiveOrganization(organizationPublicId);
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ items: [] })) as unknown as typeof fetch;

    await api("/api/v1/company/products/");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `/api/v1/organizations/${organizationPublicId}/company/products/`,
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("keeps portal management inside the organization support namespace", async () => {
    setActiveOrganization(organizationPublicId);
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ items: [] })) as unknown as typeof fetch;

    await api("/api/v1/support/portals/");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `/api/v1/organizations/${organizationPublicId}/support/portals/`,
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("fails closed when a tenant request has no selected organization", async () => {
    await expect(api("/api/v1/integrations/")).rejects.toThrow(
      "Organization context is required",
    );
  });

  it("keeps public credential routes outside the selected organization", async () => {
    setActiveOrganization(organizationPublicId);
    (globalThis as { document?: { cookie?: string } }).document = { cookie: "csrftoken=abc" };
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ ok: true })) as unknown as typeof fetch;

    await api("/api/v1/support/sessions/", { method: "POST", body: "{}" });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/support/sessions/",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
