import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

describe("product routes", () => {
  it("parses a product detail URL", () => {
    expect(routeFromPath("/products/42")).toEqual({ route: "productDetail", employeeId: null, productId: 42, productCode: null, agentId: null, releaseId: null });
  });

  it("creates a product detail URL", () => {
    expect(pathFromRoute("productDetail", 42)).toBe("/products/42");
  });
});

describe("ai agent routes", () => {
  it("parses an AI agent detail URL", () => {
    expect(routeFromPath("/ai/agents/7")).toEqual({ route: "aiAgentDetail", employeeId: null, productId: null, productCode: null, agentId: 7, releaseId: null });
  });

  it("creates an AI agent detail URL", () => {
    expect(pathFromRoute("aiAgentDetail", 7)).toBe("/ai/agents/7");
  });

  it("parses an AI agent creation URL", () => {
    expect(routeFromPath("/ai/agents/new", "?product=academy")).toEqual({ route: "aiAgentCreate", employeeId: null, productId: null, productCode: "academy", agentId: null, releaseId: null });
  });

  it("creates an AI agent creation URL", () => {
    expect(pathFromRoute("aiAgentCreate", null, "academy")).toBe("/ai/agents/new?product=academy");
  });
});

describe("ai release routes", () => {
  it("parses a release URL", () => {
    expect(routeFromPath("/ai/releases/12")).toEqual({ route: "aiRelease", employeeId: null, productId: null, productCode: null, agentId: null, releaseId: 12 });
  });

  it("creates a release URL", () => {
    expect(pathFromRoute("aiRelease", 12)).toBe("/ai/releases/12");
  });
});
