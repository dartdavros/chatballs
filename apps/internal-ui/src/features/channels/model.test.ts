import { describe, expect, it } from "vitest";

import {
  OPERATOR_POLICY,
  PRESETS,
  agentStatus,
  blockerSummary,
  connectionStatus,
  departmentTabs,
  filterChannels,
  flagLock,
  presetOf,
  slugify,
} from "./model";
import type { Channel } from "./types";

function channel(overrides: Partial<Channel>): Channel {
  return {
    id: 1,
    code: "code",
    name: "Канал",
    isActive: true,
    product: null,
    departmentId: null,
    department: null,
    departmentName: null,
    agent: null,
    connections: [],
    policy: OPERATOR_POLICY,
    counters: { openConversations: 0, connections: 0 },
    createdAt: "2026-07-01T00:00:00+00:00",
    updatedAt: "2026-07-01T00:00:00+00:00",
    ...overrides,
  };
}

describe("channel policy invariants", () => {
  it("locks commercial flags on a non-product channel", () => {
    expect(flagLock("allowCheckoutActions", OPERATOR_POLICY, false)?.rule).toBe("P1");
    expect(flagLock("allowSalesAttribution", OPERATOR_POLICY, false)?.rule).toBe("P2");
    expect(flagLock("requiresAuthenticatedProductIdentity", OPERATOR_POLICY, false)?.rule).toBe("P3");
  });

  it("unlocks commercial flags once a product is assigned", () => {
    for (const flag of ["allowCheckoutActions", "allowSalesAttribution"] as const) {
      expect(flagLock(flag, OPERATOR_POLICY, true)).toBeNull();
    }
  });

  it("locks anonymous flags while authenticated identity is required", () => {
    expect(flagLock("allowAnonymousSessions", PRESETS.SUPPORT, true)?.rule).toBe("P4");
    expect(flagLock("allowSelfReportedContact", PRESETS.SUPPORT, true)?.rule).toBe("P5");
    // Без обязательной идентичности те же флаги свободны.
    expect(flagLock("allowAnonymousSessions", PRESETS.SALES, true)).toBeNull();
  });

  it("names the preset behind a flag combination", () => {
    expect(presetOf(PRESETS.SALES)).toBe("SALES");
    expect(presetOf(PRESETS.SUPPORT)).toBe("SUPPORT");
    expect(presetOf(OPERATOR_POLICY)).toBe("CUSTOM");
  });
});

describe("channel presentation dictionaries", () => {
  it("maps backend connection states to product statuses", () => {
    expect(connectionStatus("OK")).toBe("healthy");
    expect(connectionStatus("ERROR")).toBe("error");
    expect(connectionStatus("UNKNOWN_VALUE")).toBe("unchecked");
  });

  it("maps every agent lifecycle state without exposing its code", () => {
    expect(agentStatus("ACTIVE")).toBe("active");
    expect(agentStatus("DISABLED")).toBe("disabled");
    expect(agentStatus("ARCHIVED")).toBe("archived");
    expect(agentStatus("DRAFT")).toBe("draft");
  });

  it("does not expose an unknown blocker code", () => {
    expect(blockerSummary([{ type: "unknown_table", count: 2 }])).toBe("связанные записи: 2");
  });
});

describe("channel code generation", () => {
  it("transliterates a russian name into an embeddable slug", () => {
    expect(slugify("Партнёрская линия")).toBe("partnerskaya-liniya");
    expect(slugify("FoxRay — продажи")).toBe("foxray-prodazhi");
  });

  it("never produces leading, trailing or repeated separators", () => {
    expect(slugify("  ??? Канал !!!  ")).toBe("kanal");
  });
});

describe("channel list filtering", () => {
  const channels = [
    channel({ id: 1, code: "foxray-sales", name: "FoxRay — продажи", departmentId: 1, departmentName: "Продажи" }),
    channel({ id: 2, code: "foxray-support", name: "FoxRay — поддержка", departmentId: 2, departmentName: "Поддержка" }),
    channel({ id: 3, code: "partners", name: "Партнёрская линия" }),
    channel({ id: 4, code: "old", name: "Старый", departmentId: 1, departmentName: "Продажи", isActive: false }),
  ];

  it("builds a tab per department plus «Без отдела»", () => {
    expect(departmentTabs(channels).map((tab) => [tab.key, tab.label, tab.count])).toEqual([
      ["all", "Все", 4],
      ["2", "Поддержка", 1],
      ["1", "Продажи", 2],
      ["none", "Без отдела", 1],
    ]);
  });

  it("hides archived channels until the toggle is on", () => {
    const visible = filterChannels(channels, { tab: "all", search: "", showArchived: false });
    expect(visible.map((item) => item.code)).toEqual(["foxray-sales", "foxray-support", "partners"]);

    const withArchived = filterChannels(channels, { tab: "all", search: "", showArchived: true });
    expect(withArchived).toHaveLength(4);
  });

  it("filters by department tab including channels without one", () => {
    const orphans = filterChannels(channels, { tab: "none", search: "", showArchived: false });
    expect(orphans.map((item) => item.code)).toEqual(["partners"]);
  });

  it("searches by name and code", () => {
    expect(
      filterChannels(channels, { tab: "all", search: "support", showArchived: false }).map((i) => i.code),
    ).toEqual(["foxray-support"]);
    expect(
      filterChannels(channels, { tab: "all", search: "партнёр", showArchived: false }).map((i) => i.code),
    ).toEqual(["partners"]);
  });
});
