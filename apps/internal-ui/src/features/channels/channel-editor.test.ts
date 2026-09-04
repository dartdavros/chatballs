import { describe, expect, it } from "vitest";

import {
  channelDraft,
  channelDraftChanged,
  channelDraftRequest,
  channelDraftWithProduct,
} from "./channel-editor";
import type { Channel } from "./types";

const channel: Channel = {
  id: 1,
  code: "partners",
  name: "Партнёрская линия",
  isActive: true,
  product: { id: 7, code: "foxray", name: "FoxRay" },
  groupId: 2,
  groupName: "Продажи",
  agent: null,
  connections: [],
  policy: {
    requiresAuthenticatedProductIdentity: true,
    allowAnonymousSessions: true,
    allowSelfReportedContact: true,
    allowSalesAttribution: true,
    allowCheckoutActions: true,
  },
  counters: { openConversations: 0, connections: 0 },
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

describe("channel editor", () => {
  it("creates an independent draft", () => {
    const draft = channelDraft(channel);
    draft.policy.allowAnonymousSessions = false;
    expect(channel.policy.allowAnonymousSessions).toBe(true);
  });

  it("turns off product-only policy when product is removed", () => {
    const draft = channelDraftWithProduct(channelDraft(channel), null);
    expect(draft.policy.requiresAuthenticatedProductIdentity).toBe(false);
    expect(draft.policy.allowSalesAttribution).toBe(false);
    expect(draft.policy.allowCheckoutActions).toBe(false);
    expect(draft.policy.allowAnonymousSessions).toBe(true);
  });

  it("builds one request according to edit access", () => {
    expect(channelDraftRequest(channelDraft(channel), {
      name: true,
      group: true,
      product: false,
      policy: false,
    })).toEqual({
      name: "Партнёрская линия",
      groupId: 2,
    });
  });

  it("detects draft changes", () => {
    const draft = channelDraft(channel);
    expect(channelDraftChanged(channel, draft)).toBe(false);
    draft.name = "Новое название";
    expect(channelDraftChanged(channel, draft)).toBe(true);
  });
});
