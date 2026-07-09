import { describe, expect, it } from "vitest";

import type { RouteKey } from "../types";
import { canAccess, defaultRoute } from "./access";

const OWNER_ONLY: RouteKey[] = ["command", "departments", "employees", "employeeDetail", "products", "productDetail"];
const SALES_OPERATOR_ROUTES: RouteKey[] = ["salesOverview", "salesDialogs", "salesClients", "salesClientDetail", "salesOrders", "salesOrderDetail", "profile"];
const SUPPORT_OPERATOR_ROUTES: RouteKey[] = ["supportOverview", "supportDialogs", "profile"];

describe("role access", () => {
  it("grants OWNER every route", () => {
    const all = [...OWNER_ONLY, ...SALES_OPERATOR_ROUTES, ...SUPPORT_OPERATOR_ROUTES];
    for (const route of all) {
      expect(canAccess("OWNER", route)).toBe(true);
    }
  });

  it("grants sales OPERATOR only the sales workspace and profile", () => {
    for (const route of SALES_OPERATOR_ROUTES) {
      expect(canAccess("OPERATOR", route, "sales")).toBe(true);
    }
  });

  it("blocks sales OPERATOR from support workspace and owner-only routes", () => {
    for (const route of OWNER_ONLY) {
      expect(canAccess("OPERATOR", route, "sales")).toBe(false);
    }
    expect(canAccess("OPERATOR", "supportDialogs", "sales")).toBe(false);
    expect(canAccess("OPERATOR", "supportOverview", "sales")).toBe(false);
  });

  it("grants support OPERATOR only the support workspace and profile (§10 изоляция)", () => {
    for (const route of SUPPORT_OPERATOR_ROUTES) {
      expect(canAccess("OPERATOR", route, "support")).toBe(true);
    }
    // Support operator не видит sales inbox.
    expect(canAccess("OPERATOR", "salesDialogs", "support")).toBe(false);
    expect(canAccess("OPERATOR", "salesOverview", "support")).toBe(false);
  });

  it("lands each role on its default route", () => {
    expect(defaultRoute("OWNER")).toBe("command");
    expect(defaultRoute("OPERATOR", "sales")).toBe("salesDialogs");
    expect(defaultRoute("OPERATOR", "support")).toBe("supportDialogs");
  });
});
