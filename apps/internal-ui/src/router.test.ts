import { describe, expect, it } from "vitest";

import { pathFromRoute, routeFromPath } from "./router";

const empty = {
  organizationPublicId: null,
  employeeId: null,
  agentId: null,
  knowledgeId: null,
  clientId: null,
  channelId: null,
  integrationId: null,
  supportPortalId: null,
  portalSettingsSection: null,
  settingsSection: null,
};
describe("skills library route", () => {
  it("lives under agents and preserves the organization", () => {
    const organization = "12345678-1234-1234-1234-123456789abc";
    const path = pathFromRoute("skills", null, organization);
    expect(path).toBe(`/organizations/${organization}/agents/skills`);
    expect(routeFromPath(path, "?skill=new")).toEqual({ ...empty, organizationPublicId: organization, route: "skills" });
  });
});
describe("quality analysis and evidence routes", () => {
  it("keeps the organization and conversation when analysis and its evidence are reloaded", () => {
    const organization = "12345678-1234-1234-1234-123456789abc";
    const analysis = pathFromRoute("qualityAnalysis", 12, organization);
    expect(routeFromPath(analysis)).toMatchObject({ route: "qualityAnalysis", conversationId: 12, organizationPublicId: organization });
    const chat = pathFromRoute("chat", 12, organization);
    expect(chat).toBe(`/organizations/${organization}/chat?conversation=12`);
    expect(routeFromPath(chat.split("?")[0], "?conversation=12")).toMatchObject({ route: "chat", conversationId: 12, organizationPublicId: organization });
  });
});
describe("support reports route", () => {
  it("keeps organization context in the rules and journal addresses", () => {
    const organization = "12345678-1234-1234-1234-123456789abc";
    expect(routeFromPath(pathFromRoute("ruleJournal", null, organization))).toEqual({ ...empty, organizationPublicId: organization, route: "ruleJournal" });
    expect(routeFromPath(pathFromRoute("settings", "rules", organization))).toEqual({ ...empty, organizationPublicId: organization, route: "settings", settingsSection: "rules" });
  });
  it("preserves the tenant in the statistics address and on reload", () => {
    const organization = "12345678-1234-1234-1234-123456789abc";
    const path = pathFromRoute("supportReports", null, organization);
    expect(path).toBe(`/organizations/${organization}/statistics`);
    expect(routeFromPath(path)).toEqual({ ...empty, organizationPublicId: organization, route: "supportReports" });
  });
});

describe("reply template library", () => {
  it("keeps the active organization in the employee entry point", () => {
    const organization = "12345678-1234-1234-1234-123456789abc";
    const path = pathFromRoute("replyTemplates", null, organization);
    expect(path).toBe(`/organizations/${organization}/reply-templates`);
    expect(routeFromPath(path)).toEqual({ ...empty, organizationPublicId: organization, route: "replyTemplates" });
  });
});

describe("organization create route", () => {
  // Страница создания живёт вне организации: адрес без uuid, а сборка адреса
  // не подставляет префикс текущей организации.
  it("parses and builds /organizations/new", () => {
    expect(routeFromPath("/organizations/new")).toEqual({ route: "organizationCreate", ...empty });
    expect(routeFromPath("/organizations/new/")).toEqual({ route: "organizationCreate", ...empty });
    expect(pathFromRoute("organizationCreate", null, "123e4567-e89b-12d3-a456-426614174000")).toBe("/organizations/new");
  });
});

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

describe("knowledge routes", () => {
  it("parses the library, card, editor, categories and import URLs", () => {
    expect(routeFromPath("/knowledge")).toEqual({ route: "knowledge", ...empty });
    expect(routeFromPath("/knowledge/new")).toEqual({ route: "knowledgeCreate", ...empty });
    expect(routeFromPath("/knowledge/categories")).toEqual({ route: "knowledgeCategories", ...empty });
    expect(routeFromPath("/knowledge/import")).toEqual({ route: "knowledgeImport", ...empty });
    expect(routeFromPath("/knowledge/12")).toEqual({ ...empty, route: "knowledgeDetail", knowledgeId: 12 });
    expect(routeFromPath("/knowledge/12/edit")).toEqual({ ...empty, route: "knowledgeEdit", knowledgeId: 12 });
  });

  it("keeps the legacy /ai/knowledge addresses working", () => {
    expect(routeFromPath("/ai/knowledge")).toEqual({ route: "knowledge", ...empty });
    expect(routeFromPath("/ai/knowledge/new")).toEqual({ route: "knowledgeCreate", ...empty });
    expect(routeFromPath("/ai/knowledge/12")).toEqual({ ...empty, route: "knowledgeDetail", knowledgeId: 12 });
  });

  it("creates knowledge URLs", () => {
    expect(pathFromRoute("knowledge")).toBe("/knowledge");
    expect(pathFromRoute("knowledgeCreate")).toBe("/knowledge/new");
    expect(pathFromRoute("knowledgeCategories")).toBe("/knowledge/categories");
    expect(pathFromRoute("knowledgeImport")).toBe("/knowledge/import");
    expect(pathFromRoute("knowledgeDetail", 12)).toBe("/knowledge/12");
    expect(pathFromRoute("knowledgeEdit", 12)).toBe("/knowledge/12/edit");
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
  });

  it("parses and creates administration subsection URLs", () => {
    // Организация переехала в «Настройки» (§8.6); тарифы — устаревший адрес (ADR-CHATBALLS-0042).
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
    expect(pathFromRoute("salesClients", null, organizationPublicId)).toBe(
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
    expect(routeFromPath("/ai/knowledge")).toEqual({ route: "knowledge", ...empty });
  });
});

describe("settings routes", () => {
  it("restores both external server creation pages within the organization", () => {
    const organization = "123e4567-e89b-12d3-a456-426614174000";
    for (const route of ["mcpServerCreate", "httpServerCreate"] as const) {
      const path = pathFromRoute(route, null, organization);
      expect(routeFromPath(path)).toEqual({ ...empty, organizationPublicId: organization, route });
    }
  });
  it("keeps the legacy connection id until its type is known", () => {
    expect(routeFromPath("/settings/integrations/12")).toEqual({ ...empty, route: "legacyIntegrationSettings", integrationId: 12 });
    expect(routeFromPath("/settings/integrations/12/")).toEqual({ ...empty, route: "legacyIntegrationSettings", integrationId: 12 });
    expect(routeFromPath("/settings/integrations/nope")).toEqual({ ...empty, route: "widgets" });
    expect(pathFromRoute("legacyIntegrationSettings", 12)).toBe("/settings/integrations/12");
  });

  it("parses the settings screen and its submenu sections", () => {
    expect(routeFromPath("/settings")).toEqual({ route: "settings", ...empty });
    expect(routeFromPath("/settings/groups")).toEqual({ ...empty, route: "settings", settingsSection: "groups" });
    // Неизвестный раздел открывает «Настройки» с разделом по умолчанию.
    expect(routeFromPath("/settings/nope")).toEqual({ route: "settings", ...empty });
  });

  it("creates settings URLs", () => {
    expect(pathFromRoute("settings")).toBe("/settings");
    expect(pathFromRoute("settings", "groups")).toBe("/settings/groups");
    expect(pathFromRoute("settings", "nope")).toBe("/settings");
  });
});
