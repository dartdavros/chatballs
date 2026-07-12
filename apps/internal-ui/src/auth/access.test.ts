import { describe, expect, it } from "vitest";

import type { RouteKey } from "../types";
import { canAccess, defaultRoute } from "./access";

const OWNER_ONLY: RouteKey[] = ["command", "departments", "employees", "employeeDetail", "products", "productDetail"];
const SALES_EMPLOYEE_ROUTES: RouteKey[] = ["salesOverview", "salesDialogs", "salesClients", "salesClientDetail", "salesOrders", "salesOrderDetail", "profile"];
const SUPPORT_EMPLOYEE_ROUTES: RouteKey[] = ["supportOverview", "supportDialogs", "profile"];

describe("role access", () => {
  it("grants OWNER every route", () => {
    const all = [...OWNER_ONLY, ...SALES_EMPLOYEE_ROUTES, ...SUPPORT_EMPLOYEE_ROUTES];
    for (const route of all) {
      expect(canAccess("OWNER", route)).toBe(true);
    }
  });

  it("grants sales EMPLOYEE only the sales workspace and profile", () => {
    for (const route of SALES_EMPLOYEE_ROUTES) {
      expect(canAccess("EMPLOYEE", route, "sales")).toBe(true);
    }
  });

  it("blocks sales EMPLOYEE from support workspace and owner-only routes", () => {
    for (const route of OWNER_ONLY) {
      expect(canAccess("EMPLOYEE", route, "sales")).toBe(false);
    }
    expect(canAccess("EMPLOYEE", "supportDialogs", "sales")).toBe(false);
    expect(canAccess("EMPLOYEE", "supportOverview", "sales")).toBe(false);
  });

  it("grants support EMPLOYEE only the support workspace and profile (§10 изоляция)", () => {
    for (const route of SUPPORT_EMPLOYEE_ROUTES) {
      expect(canAccess("EMPLOYEE", route, "support")).toBe(true);
    }
    // Support operator не видит sales inbox.
    expect(canAccess("EMPLOYEE", "salesDialogs", "support")).toBe(false);
    expect(canAccess("EMPLOYEE", "salesOverview", "support")).toBe(false);
  });

  it("lands each role on its default route", () => {
    expect(defaultRoute("OWNER")).toBe("command");
    expect(defaultRoute("EMPLOYEE", "sales")).toBe("salesDialogs");
    expect(defaultRoute("EMPLOYEE", "support")).toBe("supportDialogs");
  });
});
