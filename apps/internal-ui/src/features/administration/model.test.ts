import { describe, expect, it } from "vitest";

import {
  administrationSection,
  formatQuotaValue,
  subscriptionStatusLabel,
} from "./model";

describe("administration model", () => {
  it("maps administration routes to their sections", () => {
    expect(administrationSection("administrationOrganization")).toBe("organization");
    expect(administrationSection("administrationSubscription")).toBe("subscription");
    expect(administrationSection("administrationAudit")).toBe("audit");
  });

  it("formats subscription values for the product UI", () => {
    expect(formatQuotaValue(1024 ** 3, "bytes")).toBe("1 ГБ");
    expect(subscriptionStatusLabel("ACTIVE")).toBe("Активен");
    expect(subscriptionStatusLabel("UNKNOWN")).toBe("Не определён");
  });
});
