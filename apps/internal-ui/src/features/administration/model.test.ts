import { describe, expect, it } from "vitest";

import { administrationSection } from "./model";

describe("administration model", () => {
  it("maps administration routes to their sections", () => {
    expect(administrationSection("administrationAudit")).toBe("audit");
  });
});
