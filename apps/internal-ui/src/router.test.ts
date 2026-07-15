import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

const empty = {
  organizationPublicId: null,
  employeeId: null,
  productId: null,
  productCode: null,
  agentId: null,
  knowledgeId: null,
  clientId: null,
  orderId: null,
};

describe("employee access routes", () => {
  it("parses and creates the access profile URL", () => {
    expect(routeFromPath("/employees/access-profiles")).toEqual({ route: "accessProfiles", ...empty });
    expect(pathFromRoute("accessProfiles")).toBe("/employees/access-profiles");
  });
});

describe("product routes", () => {
  it("parses a product detail URL", () => {
    expect(routeFromPath("/products/42")).toEqual({ route: "productDetail", ...empty, productId: 42 });
  });

  it("creates a product detail URL", () => {
    expect(pathFromRoute("productDetail", 42)).toBe("/products/42");
  });
});

describe("sales detail routes", () => {
  it("parses a client detail URL", () => {
    expect(routeFromPath("/departments/sales/clients/15")).toEqual({ route: "salesClientDetail", ...empty, clientId: 15 });
  });

  it("parses an order detail URL", () => {
    expect(routeFromPath("/departments/sales/orders/8")).toEqual({ route: "salesOrderDetail", ...empty, orderId: 8 });
  });

  it("creates client and order detail URLs", () => {
    expect(pathFromRoute("salesClientDetail", 15)).toBe("/departments/sales/clients/15");
    expect(pathFromRoute("salesOrderDetail", 8)).toBe("/departments/sales/orders/8");
  });
});

describe("ai agent routes", () => {
  it("parses an AI agent detail URL", () => {
    expect(routeFromPath("/ai/agents/7")).toEqual({ route: "aiAgentDetail", ...empty, agentId: 7 });
  });

  it("creates an AI agent detail URL", () => {
    expect(pathFromRoute("aiAgentDetail", 7)).toBe("/ai/agents/7");
  });

  it("parses an AI agent creation URL", () => {
    expect(routeFromPath("/ai/agents/new", "?product=academy")).toEqual({ route: "aiAgentCreate", ...empty, productCode: "academy" });
  });

  it("creates an AI agent creation URL", () => {
    expect(pathFromRoute("aiAgentCreate", null, "academy")).toBe("/ai/agents/new?product=academy");
  });
});

describe("ai knowledge routes", () => {
  it("parses knowledge list and detail URLs", () => {
    expect(routeFromPath("/ai/knowledge")).toEqual({ route: "aiKnowledge", ...empty });
    expect(routeFromPath("/ai/knowledge/12")).toEqual({ route: "aiKnowledgeDetail", ...empty, knowledgeId: 12 });
  });

  it("creates knowledge URLs", () => {
    expect(pathFromRoute("aiKnowledge")).toBe("/ai/knowledge");
    expect(pathFromRoute("aiKnowledgeDetail", 12)).toBe("/ai/knowledge/12");
  });
});

describe("support routes", () => {
  it("parses support overview and dialogs URLs", () => {
    expect(routeFromPath("/departments/support")).toEqual({ route: "supportOverview", ...empty });
    expect(routeFromPath("/departments/support/dialogs")).toEqual({ route: "supportDialogs", ...empty });
  });

  it("creates support overview and dialogs URLs", () => {
    expect(pathFromRoute("supportOverview")).toBe("/departments/support");
    expect(pathFromRoute("supportDialogs")).toBe("/departments/support/dialogs");
  });
});

describe("organization routes", () => {
  const organizationPublicId = "123e4567-e89b-12d3-a456-426614174000";

  it("parses the selected organization from the URL", () => {
    expect(routeFromPath(`/organizations/${organizationPublicId}/products/42`)).toEqual({
      route: "productDetail",
      ...empty,
      organizationPublicId,
      productId: 42,
    });
  });

  it("creates navigation URLs inside the selected organization", () => {
    expect(pathFromRoute("salesOrders", null, null, organizationPublicId)).toBe(
      `/organizations/${organizationPublicId}/departments/sales/orders`,
    );
  });
});
