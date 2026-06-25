import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

describe("product routes", () => {
  it("parses a product detail URL", () => {
    expect(routeFromPath("/products/42")).toEqual({ route: "productDetail", employeeId: null, productId: 42, agentId: null });
  });

  it("creates a product detail URL", () => {
    expect(pathFromRoute("productDetail", 42)).toBe("/products/42");
  });
});

describe("ai agent routes", () => {
  it("parses an AI agent detail URL", () => {
    expect(routeFromPath("/ai/agents/7")).toEqual({ route: "aiAgentDetail", employeeId: null, productId: null, agentId: 7 });
  });

  it("creates an AI agent detail URL", () => {
    expect(pathFromRoute("aiAgentDetail", 7)).toBe("/ai/agents/7");
  });
});
