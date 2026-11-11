import { describe, expect, it } from "vitest";

import { pathFromRoute, pathFromRouteState, routeFromPath } from "./router";

const organization = "12345678-1234-1234-1234-123456789abc";
const prefix = `/organizations/${organization}`;

describe("standalone navigation routes", () => {
  it.each([
    ["aiProviders", "/ai/providers"],
    ["scenarios", "/scenarios"],
    ["widgets", "/widgets"],
    ["messengers", "/messengers"],
    ["emailIntegrations", "/mail"],
    ["integrationServers", "/tools"],
    ["mcpServerCreate", "/tools/new/mcp"],
    ["httpServerCreate", "/tools/new/http"],
    ["serviceIntegrations", "/integrations"],
  ] as const)("opens %s directly within the active organization", (route, suffix) => {
    expect(pathFromRoute(route, null, organization)).toBe(`${prefix}${suffix}`);
    expect(routeFromPath(`${prefix}${suffix}`)).toMatchObject({ route, organizationPublicId: organization });
  });

  it.each([
    ["webIntegrationSettings", "/widgets/12"],
    ["externalServerSettings", "/tools/12"],
    ["serviceConnection", "/integrations/12"],
  ] as const)("restores the selected connection for %s", (route, suffix) => {
    const path = pathFromRoute(route, 12, organization);
    expect(path).toBe(`${prefix}${suffix}`);
    const state = routeFromPath(`${path}/`);
    expect(state).toMatchObject({ route, integrationId: 12, organizationPublicId: organization });
    expect(pathFromRouteState(state)).toBe(path);
  });

  it.each([
    ["/widgets/nope", "widgets"],
    ["/tools/0", "integrationServers"],
    ["/tools/-1", "integrationServers"],
    ["/tools/9007199254740992", "integrationServers"],
    ["/integrations/1/unknown", "serviceIntegrations"],
  ] as const)("falls back to its own list for %s", (suffix, route) => {
    expect(routeFromPath(`${prefix}${suffix}`)).toMatchObject({ route, integrationId: null, organizationPublicId: organization });
  });
});

describe("legacy navigation addresses", () => {
  it.each([
    ["/settings/ai", "/ai/providers"],
    ["/settings/scenarios", "/scenarios"],
    ["/settings/integrations", "/widgets"],
    ["/settings/integrations/servers", "/tools"],
    ["/settings/integrations/new/mcp", "/tools/new/mcp"],
    ["/settings/integrations/new/http", "/tools/new/http"],
    ["/settings/integrations/services", "/integrations"],
    ["/settings/integrations/services/27", "/integrations/27"],
  ])("resolves %s without losing the organization or id", (oldPath, newPath) => {
    const state = routeFromPath(`${prefix}${oldPath}`);
    expect(state).toEqual(routeFromPath(`${prefix}${newPath}`));
    expect(pathFromRouteState(state)).toBe(`${prefix}${newPath}`);
  });

  it("does not guess whether a legacy connection is a widget or an external server", () => {
    const oldPath = `${prefix}/settings/integrations/31`;
    const state = routeFromPath(oldPath);
    expect(state).toMatchObject({ route: "legacyIntegrationSettings", integrationId: 31 });
    expect(pathFromRouteState(state)).toBe(oldPath);
    expect(pathFromRouteState({ ...state, route: "externalServerSettings" })).toBe(`${prefix}/tools/31`);
    expect(pathFromRouteState({ ...state, route: "webIntegrationSettings" })).toBe(`${prefix}/widgets/31`);
  });

  it.each([
    "?scenario=52ef5ad7-49a2-4999-a9a2-3e3e4a4f6569",
    "?runs=1&run=fae35075-f599-4fdb-8074-4f799932ce24",
  ])("keeps scenario workspace selection during canonicalization: %s", search => {
    const state = routeFromPath(`${prefix}/settings/scenarios`, search);
    expect(pathFromRouteState(state, undefined, search)).toBe(`${prefix}/scenarios${search}`);
  });
});

describe("canonical route state", () => {
  it.each([
    "/employees/42", "/agents/17", "/contacts/19", "/knowledge/22",
    "/knowledge/22/edit", "/portals/7", "/portals/7/settings/theme",
    "/settings/groups", "/conversations/14/quality",
  ])("retains the selected entity or section when adding organization to %s", path => {
    expect(pathFromRouteState(routeFromPath(path), organization)).toBe(`${prefix}${path}`);
  });

  it("preserves an explicit portal section, not just the portal id", () => {
    const state = routeFromPath(`${prefix}/portals/18/settings/domain`);
    expect(pathFromRouteState(state)).toBe(`${prefix}/portals/18/settings/domain`);
  });

  it("merges search without overriding the conversation stored in the route", () => {
    const state = routeFromPath(`${prefix}/chat`, "?conversation=12");
    expect(pathFromRouteState(state, undefined, "?conversation=99&focus=message-4"))
      .toBe(`${prefix}/chat?conversation=12&focus=message-4`);
  });

  it("adds optional query to a programmatic scenario navigation", () => {
    expect(pathFromRoute("scenarios", null, organization, "runs=1&run=123"))
      .toBe(`${prefix}/scenarios?runs=1&run=123`);
  });

  it("keeps creating an organization outside the current organization", () => {
    expect(pathFromRouteState(routeFromPath("/organizations/new"), organization)).toBe("/organizations/new");
  });
});
