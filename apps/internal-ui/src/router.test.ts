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
  portalSettingsSection: null,
  settingsSection: null,
};

describe("sales detail routes", () => {
  it("parses a client detail URL", () => {
    expect(routeFromPath("/departments/sales/clients/15")).toEqual({ route: "salesClientDetail", ...empty, clientId: 15 });
  });

  it("creates a client detail URL", () => {
    expect(pathFromRoute("salesClientDetail", 15)).toBe("/contacts/15");
    expect(routeFromPath("/contacts/15")).toEqual({ route: "salesClientDetail", ...empty, clientId: 15 });
    expect(pathFromRoute("supportPortalDetail", 3)).toBe("/portals/3");
    expect(routeFromPath("/portals/3")).toEqual({ route: "supportPortalDetail", ...empty, supportPortalId: 3 });
  });

  // Настройки портала — страница с субменю разделов, а не модалка (кадры PT4–PT6).
  it("parses and builds portal settings URLs", () => {
    expect(routeFromPath("/portals/3/settings")).toEqual({
      ...empty,
      route: "supportPortalSettings",
      supportPortalId: 3,
      portalSettingsSection: "basics",
    });
    expect(routeFromPath("/portals/3/settings/theme")).toEqual({
      ...empty,
      route: "supportPortalSettings",
      supportPortalId: 3,
      portalSettingsSection: "theme",
    });
    // Неизвестный раздел открывает первый.
    expect(routeFromPath("/portals/3/settings/nope")).toEqual({
      ...empty,
      route: "supportPortalSettings",
      supportPortalId: 3,
      portalSettingsSection: "basics",
    });
    expect(pathFromRoute("supportPortalSettings", "3/domain")).toBe("/portals/3/settings/domain");
    expect(pathFromRoute("supportPortalSettings", "3/")).toBe("/portals/3/settings/basics");
  });
});

describe("agent routes", () => {
  it("parses an agent detail URL", () => {
    expect(routeFromPath("/agents/7")).toEqual({ route: "agentDetail", ...empty, agentId: 7 });
  });

  it("creates an agent detail URL", () => {
    expect(pathFromRoute("agentDetail", 7)).toBe("/agents/7");
    expect(pathFromRoute("agentDetail", null)).toBe("/agents");
  });

  it("redirects legacy ai agent URLs to the unified section", () => {
    expect(routeFromPath("/ai/agents/7")).toEqual({ route: "agents", ...empty });
    expect(routeFromPath("/ai/agents/new")).toEqual({ route: "agents", ...empty });
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
  it("redirects the legacy support overview URL to the board", () => {
    expect(routeFromPath("/departments/support")).toEqual({ route: "supportPortals", ...empty });
  });
});

describe("chat route", () => {
  it("parses /chat and the legacy dialog URLs", () => {
    expect(routeFromPath("/chat")).toEqual({ route: "chat", ...empty });
    expect(routeFromPath("/departments/sales/dialogs")).toEqual({ route: "chat", ...empty });
    expect(routeFromPath("/departments/support/dialogs")).toEqual({ route: "chat", ...empty });
  });

  it("creates the chat URL", () => {
    expect(pathFromRoute("chat")).toBe("/chat");
  });
});

describe("administration route", () => {
  it("sends legacy administration URLs to settings (§8.6)", () => {
    expect(routeFromPath("/administration")).toEqual({
      ...empty,
      route: "settings",
      settingsSection: "organization",
    });
    expect(routeFromPath("/integrations")).toEqual({
      ...empty,
      route: "settings",
      settingsSection: "integrations",
    });
  });

  it("parses and creates administration subsection URLs", () => {
    // Организация переехала в «Настройки» (§8.6); тарифы — устаревший адрес (ADR-HUB-0042).
    expect(routeFromPath("/administration/organization")).toEqual({
      ...empty,
      route: "settings",
      settingsSection: "organization",
    });
    expect(routeFromPath("/administration/subscription")).toEqual({
      ...empty,
      route: "settings",
      settingsSection: "organization",
    });
    expect(routeFromPath("/administration/audit")).toEqual({
      route: "administrationAudit",
      ...empty,
    });
    expect(pathFromRoute("administrationAudit")).toBe("/administration/audit");
  });
});

describe("support portal routes", () => {
  it("parses support portal list and detail URLs", () => {
    expect(routeFromPath("/departments/support/portals")).toEqual({ route: "supportPortals", ...empty });
    expect(routeFromPath("/departments/support/portals/9")).toEqual({ route: "supportPortalDetail", ...empty, supportPortalId: 9 });
  });

  it("creates support portal URLs", () => {
    expect(pathFromRoute("supportPortals")).toBe("/portals");
    expect(pathFromRoute("supportPortalDetail", 9)).toBe("/portals/9");
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
      `/organizations/${organizationPublicId}/contacts`,
    );
  });
});

describe("channel routes", () => {
  it("parses the list, wizard and card URLs", () => {
    expect(routeFromPath("/channels")).toEqual({ route: "agents", ...empty });
    expect(routeFromPath("/channels/12")).toEqual({ route: "agentDetail", ...empty, agentId: 12 });
  });

  it("falls back to the list for a malformed channel id", () => {
    expect(routeFromPath("/channels/abc")).toEqual({ route: "agents", ...empty });
  });

  it("keeps AI routes untouched", () => {
    expect(routeFromPath("/ai/agents")).toEqual({ route: "agents", ...empty });
    expect(routeFromPath("/ai/knowledge")).toEqual({ route: "aiKnowledge", ...empty });
  });
});

describe("settings routes", () => {
  it("parses the settings screen and its submenu sections", () => {
    expect(routeFromPath("/settings")).toEqual({ route: "settings", ...empty });
    expect(routeFromPath("/settings/groups")).toEqual({ ...empty, route: "settings", settingsSection: "groups" });
    // Неизвестный раздел открывает «Настройки» с разделом по умолчанию.
    expect(routeFromPath("/settings/nope")).toEqual({ route: "settings", ...empty });
  });

  it("creates settings URLs", () => {
    expect(pathFromRoute("settings")).toBe("/settings");
    expect(pathFromRoute("settings", "integrations")).toBe("/settings/integrations");
    expect(pathFromRoute("settings", "nope")).toBe("/settings");
  });
});
