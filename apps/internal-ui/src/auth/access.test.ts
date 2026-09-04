import { describe, expect, it } from "vitest";

import { canAccess, defaultRoute, hasCapability, isManager } from "./access";
import type { Role, SessionUser } from "../types";

function userWith(role: Role, capabilities: string[] = []): SessionUser {
  return {
    id: 1,
    email: "user@example.test",
    fullName: "Test User",
    mustChangePassword: false,
    totpEnabled: false,
    deliveryMode: "CLOUD",
  uiTheme: "SYSTEM",
  uiAccent: "",
    memberships: [],
    organizationPublicId: "org-1",
    organization: "org",
    organizationName: "Org",
    organizationLogoUrl: null,
    role,
    positionTitle: "Специалист",
    totpRequired: false,
    capabilities,
    groups: [],
  };
}

describe("role-based navigation (SPEC-HUB-0031 §3)", () => {
  it("gives owner and admin identical full access", () => {
    for (const role of ["OWNER", "ADMIN"] as const) {
      const user = userWith(role);
      expect(isManager(user)).toBe(true);
      expect(canAccess(user, "command")).toBe(true);
      expect(canAccess(user, "employees")).toBe(true);
      expect(canAccess(user, "agents")).toBe(true);
      expect(canAccess(user, "aiKnowledge")).toBe(true);
      expect(canAccess(user, "administrationOrganization")).toBe(true);
      expect(defaultRoute(user)).toBe("command");
    }
  });

  it("limits employee to the chat plus self-service", () => {
    const user = userWith("EMPLOYEE");
    expect(isManager(user)).toBe(false);
    expect(canAccess(user, "salesDialogs")).toBe(true);
    expect(canAccess(user, "supportDialogs")).toBe(true);
    expect(canAccess(user, "profile")).toBe(true);
    expect(canAccess(user, "settings")).toBe(true);
    expect(canAccess(user, "employees")).toBe(false);
    expect(canAccess(user, "agents")).toBe(false);
    expect(canAccess(user, "aiKnowledge")).toBe(false);
    expect(canAccess(user, "salesClients")).toBe(false);
    expect(defaultRoute(user)).toBe("salesDialogs");
  });

  it("reads capabilities straight from the session payload", () => {
    const user = userWith("EMPLOYEE", ["conversations.view"]);
    expect(hasCapability(user, "conversations.view")).toBe(true);
    expect(hasCapability(user, "ai.manage")).toBe(false);
  });
});
