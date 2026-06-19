import { describe, expect, it } from "vitest";

import type { RouteKey } from "../types";
import { canAccess, defaultRoute } from "./access";

const OWNER_ONLY: RouteKey[] = ["command", "departments", "employees", "employeeDetail", "products", "productDetail"];
const OPERATOR_ALLOWED: RouteKey[] = ["salesOverview", "salesDialogs", "salesClients", "salesClientDetail", "salesOrders", "salesOrderDetail", "profile"];

describe("role access", () => {
  it("grants OWNER every route", () => {
    for (const route of [...OWNER_ONLY, ...OPERATOR_ALLOWED]) {
      expect(canAccess("OWNER", route)).toBe(true);
    }
  });

  it("grants OPERATOR only the sales workspace and profile", () => {
    for (const route of OPERATOR_ALLOWED) {
      expect(canAccess("OPERATOR", route)).toBe(true);
    }
  });

  it("blocks OPERATOR from owner-only routes", () => {
    for (const route of OWNER_ONLY) {
      expect(canAccess("OPERATOR", route)).toBe(false);
    }
  });

  it("lands each role on its default route", () => {
    expect(defaultRoute("OWNER")).toBe("command");
    expect(defaultRoute("OPERATOR")).toBe("salesDialogs");
  });
});
