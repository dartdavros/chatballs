import { describe, expect, it } from "vitest";

import type { SessionUser } from "../types";
import { canAccess, defaultRoute, scopeDepartments } from "./access";

const baseUser: Omit<SessionUser, "role" | "capabilities" | "accessScopes" | "memberships"> = {
  id: 1,
  email: "employee@example.test",
  fullName: "Employee",
  organizationPublicId: "00000000-0000-4000-8000-000000000001",
  positionTitle: "Specialist",
  organization: "example",
  organizationName: "Example",
  organizationLogoUrl: null,
  department: null,
  mustChangePassword: false,
  totpRequired: false,
  totpEnabled: false,
  deliveryMode: "CLOUD",
};

function userWith(
  capabilities: string[],
  departmentCode: string | null = null,
): SessionUser {
  const membership = {
    id: baseUser.id,
    organizationPublicId: baseUser.organizationPublicId,
    organization: baseUser.organization,
    organizationName: baseUser.organizationName,
    organizationLogoUrl: baseUser.organizationLogoUrl,
    role: "EMPLOYEE" as const,
    positionTitle: baseUser.positionTitle,
    department: baseUser.department,
    totpRequired: baseUser.totpRequired,
    capabilities,
    accessScopes: [
      {
        scopeType: departmentCode ? "DEPARTMENT" as const : "ORGANIZATION" as const,
        departmentId: departmentCode ? 10 : null,
        departmentCode,
        capabilities,
      },
    ],
  };
  return {
    ...baseUser,
    ...membership,
    memberships: [membership],
  };
}

describe("effective access navigation", () => {
  it("uses organization capabilities instead of the system role", () => {
    const user = userWith(["company.view", "employees.view", "employees.manage", "products.view"]);
    expect(canAccess(user, "command")).toBe(true);
    expect(canAccess(user, "employees")).toBe(true);
    expect(canAccess(user, "accessProfiles")).toBe(true);
    expect(canAccess(user, "products")).toBe(true);
    expect(canAccess(user, "administrationOrganization")).toBe(false);
    expect(canAccess(user, "integrations")).toBe(false);
    expect(defaultRoute(user)).toBe("command");
  });

  it("opens administration subsections only with their capabilities", () => {
    const settingsUser = userWith(["settings.view"]);
    const auditUser = userWith(["audit.view"]);
    expect(canAccess(settingsUser, "administrationOrganization")).toBe(true);
    expect(canAccess(settingsUser, "administrationSubscription")).toBe(true);
    expect(canAccess(settingsUser, "administrationAudit")).toBe(false);
    expect(canAccess(auditUser, "administrationOrganization")).toBe(false);
    expect(canAccess(auditUser, "administrationAudit")).toBe(true);
  });

  it("does not expose the cloud subscription in a self-hosted installation", () => {
    const user = userWith(["settings.view"]);
    user.deliveryMode = "SELF_HOSTED";
    expect(canAccess(user, "administrationSubscription")).toBe(false);
  });

  it("keeps sales and support department scopes isolated", () => {
    const capabilities = ["conversations.view", "sales.view", "customers.view"];
    const sales = userWith(capabilities, "sales");
    const support = userWith(["conversations.view", "support.view"], "support");

    expect(canAccess(sales, "salesDialogs")).toBe(true);
    expect(canAccess(sales, "supportDialogs")).toBe(false);
    expect(canAccess(sales, "supportPortals")).toBe(false);
    expect(canAccess(support, "supportDialogs")).toBe(true);
    expect(canAccess(support, "supportPortals")).toBe(true);
    expect(canAccess(support, "salesDialogs")).toBe(false);
  });

  it("combines multiple department assignments", () => {
    const user = userWith([], "sales");
    user.capabilities = ["conversations.view"];
    user.accessScopes = [
      { scopeType: "DEPARTMENT", departmentId: 10, departmentCode: "sales", capabilities: ["conversations.view"] },
      { scopeType: "DEPARTMENT", departmentId: 20, departmentCode: "support", capabilities: ["conversations.view"] },
    ];
    expect(canAccess(user, "salesDialogs")).toBe(true);
    expect(canAccess(user, "supportDialogs")).toBe(true);
    expect(defaultRoute(user)).toBe("salesDialogs");
  });

  it("falls back to self-service profile when no work capability is assigned", () => {
    const user = userWith([]);
    expect(canAccess(user, "profile")).toBe(true);
    expect(defaultRoute(user)).toBe("profile");
  });

  it("reports organization-wide access without a department list", () => {
    expect(scopeDepartments(userWith(["channels.view"]), "channels.view")).toBeNull();
  });

  it("returns the unique department subset for an assigned capability", () => {
    const user = userWith(["channels.view"], "sales");
    user.accessScopes.push({
      scopeType: "DEPARTMENT",
      departmentId: 10,
      departmentCode: "sales",
      capabilities: ["channels.view"],
    });
    user.accessScopes.push({
      scopeType: "DEPARTMENT",
      departmentId: 20,
      departmentCode: "support",
      capabilities: ["channels.view"],
    });
    expect(scopeDepartments(user, "channels.view")).toEqual(["sales", "support"]);
  });

  it("returns an empty subset when the capability is not assigned", () => {
    expect(scopeDepartments(userWith([]), "channels.view")).toEqual([]);
  });
});
