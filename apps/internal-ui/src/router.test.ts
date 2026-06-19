import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

describe("product routes", () => {
  it("parses a product detail URL", () => {
    expect(routeFromPath("/products/42")).toEqual({ route: "productDetail", employeeId: null, productId: 42 });
  });

  it("creates a product detail URL", () => {
    expect(pathFromRoute("productDetail", 42)).toBe("/products/42");
  });
});
