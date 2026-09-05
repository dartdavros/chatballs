import { afterEach, describe, expect, it, vi } from "vitest";

import { setActiveOrganization } from "../../../api/client";
import {
  bulkMoveKnowledge,
  createKnowledgeCategory,
  fetchKnowledgeCategories,
  fetchKnowledgeList,
  linkKnowledgeToAgent,
  linkPortalArticlesToAgent,
  selectAgentCategoryKnowledge,
  updateKnowledgeCategory,
} from "./api";

const organizationPublicId = "123e4567-e89b-12d3-a456-426614174000";
const originalFetch = globalThis.fetch;
const originalDocumentCookie = (globalThis as { document?: { cookie?: string } }).document?.cookie;

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

afterEach(() => {
  setActiveOrganization(null);
  globalThis.fetch = originalFetch;
  if (originalDocumentCookie === undefined) {
    delete (globalThis as { document?: { cookie?: string } }).document;
  }
  vi.restoreAllMocks();
});

function mockSuccess(body: unknown = {}): ReturnType<typeof vi.fn> {
  const mocked = vi.fn().mockResolvedValue(jsonResponse(body));
  globalThis.fetch = mocked as unknown as typeof fetch;
  (globalThis as { document?: { cookie?: string } }).document = { cookie: "csrftoken=abc" };
  setActiveOrganization(organizationPublicId);
  return mocked;
}

describe("knowledge API", () => {
  it("sends list filters to the backend", async () => {
    const fetchMock = mockSuccess({ items: [] });

    await fetchKnowledgeList({
      category: 7,
      isEnabled: false,
      search: "тариф Acme",
    });

    const url = new URL(fetchMock.mock.calls[0][0], "https://app.example");
    expect(url.pathname).toBe(
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/`,
    );
    expect(Object.fromEntries(url.searchParams)).toEqual({
      category: "7",
      isEnabled: "false",
      search: "тариф Acme",
    });
  });

  it("uses the category list, create and update contracts", async () => {
    const fetchMock = mockSuccess({ items: [] });

    await fetchKnowledgeCategories();
    await createKnowledgeCategory({ name: "Acme", parentId: 3, sortOrder: 20 });
    await updateKnowledgeCategory(7, { name: "Acme Pro", parentId: null, sortOrder: 30 });

    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/categories/`,
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/categories/`,
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/categories/7/`,
    ]);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      name: "Acme",
      parentId: 3,
      sortOrder: 20,
    });
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({
      name: "Acme Pro",
      parentId: null,
      sortOrder: 30,
    });
  });

  it("uses dedicated bulk and agent category-selection endpoints", async () => {
    const fetchMock = mockSuccess({ updated: 2, knowledgeIds: [10, 11] });

    await bulkMoveKnowledge({ knowledgeIds: [10, 11], categoryId: 5 });
    await selectAgentCategoryKnowledge(9, 5);

    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/bulk/move/`,
      `/api/v1/organizations/${organizationPublicId}/ai/agents/9/knowledge/select-category/`,
    ]);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      knowledgeIds: [10, 11],
      categoryId: 5,
    });
  });

  it("sends agent link requests for both libraries", async () => {
    const fetchMock = mockSuccess({ agentId: 9, action: "attach", changed: 2, changedIds: [10, 11], skippedIds: [] });

    await linkKnowledgeToAgent({ agentId: 9, action: "attach", knowledgeIds: [10, 11] });
    await linkPortalArticlesToAgent({ agentId: 9, action: "detach", articleIds: [4] });

    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      `/api/v1/organizations/${organizationPublicId}/ai/knowledge/bulk/agent/`,
      `/api/v1/organizations/${organizationPublicId}/ai/portal-articles/bulk/agent/`,
    ]);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      agentId: 9,
      action: "attach",
      knowledgeIds: [10, 11],
    });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      agentId: 9,
      action: "detach",
      articleIds: [4],
    });
  });
});
