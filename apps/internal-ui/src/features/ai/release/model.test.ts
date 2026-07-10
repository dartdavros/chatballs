import { describe, expect, it } from "vitest";

import type { AiReleaseFull } from "../detail/model";
import { buildChecks, canPublishRelease } from "./model";

const channel = { id: 1, code: "edeves", name: "Edeves", product: null };

function buildRelease(overrides: Partial<AiReleaseFull> = {}): AiReleaseFull {
  return {
    id: 1,
    channel,
    version: 1,
    status: "DRAFT",
    model: "anthropic/claude-sonnet-4.6",
    modelParams: {},
    allowedTools: [{ name: "handoff" }],
    limits: { dailyCostUsd: 500 },
    notes: "",
    retrievalIndexVersion: "",
    knowledgeVersions: [{ document: "overview", version: 1 }],
    promptVersions: [
      { document: "system", version: 1 },
      { document: "sales", version: 1 },
    ],
    createdAt: "2026-07-01T00:00:00Z",
    publishedAt: null,
    ...overrides,
  };
}

describe("release publish gate", () => {
  it("publishes a draft without a built retrieval index", () => {
    const release = buildRelease({ retrievalIndexVersion: "" });
    const checks = buildChecks(release);

    expect(checks.some((check) => check.label.includes("Retrieval"))).toBe(false);
    expect(canPublishRelease(release, checks)).toBe(true);
  });

  it("publishes a draft without a sales prompt (sales-behavior gate removed)", () => {
    const release = buildRelease({ promptVersions: [{ document: "system", version: 1 }] });
    const checks = buildChecks(release);

    expect(checks.some((check) => check.label.includes("Sales"))).toBe(false);
    expect(canPublishRelease(release, checks)).toBe(true);
  });

  it("stays blocked when the release is not a draft", () => {
    const release = buildRelease({ status: "PUBLISHED" });
    expect(canPublishRelease(release, buildChecks(release))).toBe(false);
  });

  it("stays blocked when a required section is missing", () => {
    const release = buildRelease({ promptVersions: [] });
    expect(canPublishRelease(release, buildChecks(release))).toBe(false);
  });

  it("stays blocked when tools or limits are empty", () => {
    const release = buildRelease({ allowedTools: [], limits: {} });
    expect(canPublishRelease(release, buildChecks(release))).toBe(false);
  });
});
