import { describe, expect, it } from "vitest";

import { canAccess, canViewRuleJournal, defaultRoute, hasCapability, isManager } from "./access";
import type { Role, SessionUser } from "../types";

function userWith(role: Role, capabilities: string[] = []): SessionUser {
  return {
    id: 1,
    email: "user@example.test",
    fullName: "Test User",
    mustChangePassword: false,
    totpEnabled: false,
    totpLastUsedAt: null,
    deliveryMode: "CLOUD",
    isInstanceAdmin: false,
    uiTheme: "SYSTEM",
    uiAccent: "",
    uiLanguage: "",
    language: "ru",
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
    joinedAt: "2026-01-01T00:00:00Z",
  };
}

const standaloneManagementRoutes = [
  "aiProviders", "scenarios", "widgets", "messengers", "emailIntegrations",
  "integrationServers", "mcpServerCreate", "httpServerCreate", "externalServerSettings",
  "webIntegrationSettings", "legacyIntegrationSettings", "serviceIntegrations", "serviceConnection",
] as const;

describe("role-based navigation (SPEC-CHATBALLS-0031 §3)", () => {
  it.each(["OWNER", "ADMIN"] as const)("keeps access to extracted settings and their direct links for %s", role => {
    for (const route of standaloneManagementRoutes) {
      expect(canAccess(userWith(role), route), route).toBe(true);
    }
  });

  it.each(["EMPLOYEE", "SUPERVISOR"] as const)("does not expose extracted settings through direct links to %s", role => {
    const user = {
      ...userWith(role, ["integrations.view", "integrations.manage", "ai.manage"]),
      reportCapabilities: ["reports.view"],
      supervisedGroups: [{ id: 1, name: "Support" }],
    };
    for (const route of standaloneManagementRoutes) {
      expect(canAccess(user, route), route).toBe(false);
    }
  });

  it("opens the scoped rule journal without granting supervisors settings", () => {
    const supervisor = { ...userWith("SUPERVISOR"), supervisedGroups: [{ id: 1, name: "Support" }] };
    expect(canViewRuleJournal(supervisor)).toBe(true);
    expect(canAccess(supervisor, "ruleJournal")).toBe(true);
    expect(canAccess(supervisor, "settings")).toBe(false);
    expect(canAccess(userWith("SUPERVISOR"), "ruleJournal")).toBe(false);
    expect(canAccess(userWith("EMPLOYEE"), "ruleJournal")).toBe(false);
  });
  it("uses the effective report grant for supervisors without opening administration", () => {
    for (const role of ["OWNER", "ADMIN"] as const) expect(canAccess(userWith(role), "supportReports")).toBe(true);
    for (const role of ["EMPLOYEE", "SUPERVISOR"] as const) expect(canAccess(userWith(role), "supportReports")).toBe(false);
    expect(canAccess({ ...userWith("SUPERVISOR"), reportCapabilities: ["reports.view"] }, "supportReports")).toBe(true);
  });
  it("does not give supervisors administrative routes", () => {
    const user = userWith("SUPERVISOR", ["conversations.assign"]);
    expect(isManager(user)).toBe(false);
    for (const route of ["employees", "settings", "agents", "skills", "administrationAudit"] as const) expect(canAccess(user, route)).toBe(false);
    expect(canAccess(user, "chat")).toBe(true);
    expect(canAccess(user, "qualityAnalysis")).toBe(true);
    expect(canAccess(userWith("EMPLOYEE"), "qualityAnalysis")).toBe(false);
  });
  it("gives owner and admin identical full access", () => {
    for (const role of ["OWNER", "ADMIN"] as const) {
      const user = userWith(role);
      expect(isManager(user)).toBe(true);
      expect(canAccess(user, "employees")).toBe(true);
      expect(canAccess(user, "agents")).toBe(true);
      expect(canAccess(user, "skills")).toBe(true);
      expect(canAccess(user, "mcpServerCreate")).toBe(true);
      expect(canAccess(user, "httpServerCreate")).toBe(true);
      expect(canAccess(user, "knowledge")).toBe(true);
      expect(canAccess(user, "administrationAudit")).toBe(true);
      expect(defaultRoute(user)).toBe("chat");
    }
  });

  it("limits employee to the chat plus self-service", () => {
    const user = userWith("EMPLOYEE");
    expect(isManager(user)).toBe(false);
    expect(canAccess(user, "chat")).toBe(true);
    expect(canAccess(user, "profile")).toBe(true);
    expect(canAccess(user, "replyTemplates")).toBe(true);
    // «Настройки» — настройки организации, сотруднику недоступны (дизайн-базлайн v2).
    expect(canAccess(user, "settings")).toBe(false);
    expect(canAccess(user, "mcpServerCreate")).toBe(false);
    expect(canAccess(user, "httpServerCreate")).toBe(false);
    expect(canAccess(user, "employees")).toBe(false);
    expect(canAccess(user, "agents")).toBe(false);
    expect(canAccess(user, "knowledge")).toBe(false);
    expect(canAccess(user, "salesClients")).toBe(false);
    expect(defaultRoute(user)).toBe("chat");
  });

  it("reads capabilities straight from the session payload", () => {
    const user = userWith("EMPLOYEE", ["conversations.view"]);
    expect(hasCapability(user, "conversations.view")).toBe(true);
    expect(hasCapability(user, "ai.manage")).toBe(false);
  });
});
