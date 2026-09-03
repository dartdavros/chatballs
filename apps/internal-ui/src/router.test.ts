import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

const empty = {
  organizationPublicId: null,
  employeeId: null,
  productCode: null,
  agentId: null,
  knowledgeId: null,
  clientId: null,
  channelId: null,
  supportPortalId: null,
};

describe("employee access routes", () => {
  it("parses and creates the access profile URL", () => {
    expect(routeFromPath("/employees/access-profiles")).toEqual({ route: "accessProfiles", ...empty });
    expect(pathFromRoute("accessProfiles")).toBe("/employees/access-profiles");
  });
});

describe("sales detail routes", () => {
  it("parses a client detail URL", () => {
    expect(routeFromPath("/departments/sales/clients/15")).toEqual({ route: "salesClientDetail", ...empty, clientId: 15 });
  });

  it("creates a client detail URL", () => {
    expect(pathFromRoute("salesClientDetail", 15)).toBe("/departments/sales/clients/15");
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
    expect(routeFromPath("/ai/knowledge/new")).toEqual({ route: "aiKnowledgeCreate", ...empty });
    expect(routeFromPath("/ai/knowledge/12")).toEqual({ route: "aiKnowledgeDetail", ...empty, knowledgeId: 12 });
  });

  it("creates knowledge URLs", () => {
    expect(pathFromRoute("aiKnowledge")).toBe("/ai/knowledge");
    expect(pathFromRoute("aiKnowledgeCreate")).toBe("/ai/knowledge/new");
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

describe("administration route", () => {
  it("keeps the old URL as an organization alias", () => {
    expect(routeFromPath("/administration")).toEqual({
      route: "administrationOrganization",
      ...empty,
    });
  });

  it("parses and creates administration subsection URLs", () => {
    expect(routeFromPath("/administration/organization")).toEqual({
      route: "administrationOrganization",
      ...empty,
    });
    expect(routeFromPath("/administration/subscription")).toEqual({
      route: "administrationSubscription",
      ...empty,
    });
    expect(routeFromPath("/administration/audit")).toEqual({
      route: "administrationAudit",
      ...empty,
    });
    expect(pathFromRoute("administrationOrganization")).toBe("/administration/organization");
    expect(pathFromRoute("administrationSubscription")).toBe("/administration/subscription");
    expect(pathFromRoute("administrationAudit")).toBe("/administration/audit");
  });
});

describe("support portal routes", () => {
  it("parses support portal list and detail URLs", () => {
    expect(routeFromPath("/departments/support/portals")).toEqual({ route: "supportPortals", ...empty });
    expect(routeFromPath("/departments/support/portals/9")).toEqual({ route: "supportPortalDetail", ...empty, supportPortalId: 9 });
  });

  it("creates support portal URLs", () => {
    expect(pathFromRoute("supportPortals")).toBe("/departments/support/portals");
    expect(pathFromRoute("supportPortalDetail", 9)).toBe("/departments/support/portals/9");
  });
});

describe("organization routes", () => {
  const organizationPublicId = "123e4567-e89b-12d3-a456-426614174000";

  it("parses the selected organization from the URL", () => {
    expect(routeFromPath(`/organizations/${organizationPublicId}/employees/42`)).toEqual({
      route: "employeeDetail",
      ...empty,
      organizationPublicId,
      employeeId: 42,
    });
  });

  it("creates navigation URLs inside the selected organization", () => {
    expect(pathFromRoute("salesClients", null, null, organizationPublicId)).toBe(
      `/organizations/${organizationPublicId}/departments/sales/clients`,
    );
  });
});

describe("channel routes", () => {
  it("parses the list, wizard and card URLs", () => {
    expect(routeFromPath("/channels")).toEqual({ route: "channels", ...empty });
    expect(routeFromPath("/channels/new")).toEqual({ route: "channelCreate", ...empty });
    expect(routeFromPath("/channels/12")).toEqual({ route: "channelDetail", ...empty, channelId: 12 });
  });

  it("falls back to the list for a malformed channel id", () => {
    expect(routeFromPath("/channels/abc")).toEqual({ route: "channels", ...empty });
  });

  it("builds channel paths", () => {
    expect(pathFromRoute("channels")).toBe("/channels");
    expect(pathFromRoute("channelCreate")).toBe("/channels/new");
    expect(pathFromRoute("channelDetail", 12)).toBe("/channels/12");
    expect(pathFromRoute("channelDetail", null)).toBe("/channels");
  });

  it("keeps AI routes untouched", () => {
    expect(routeFromPath("/ai/agents")).toEqual({ route: "aiAgents", ...empty });
    expect(routeFromPath("/ai/knowledge")).toEqual({ route: "aiKnowledge", ...empty });
    expect(pathFromRoute("aiAgentDetail", 7)).toBe("/ai/agents/7");
  });
});
