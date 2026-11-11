import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, describe, expect, it, vi } from "vitest";
import { t } from "../../i18n";
import { ConnectionsTable } from "./ConnectionsTable";
import { integrationProviderOptions } from "./integrationFormModel";
import { IntegrationWorkspacePage } from "./IntegrationWorkspacePage";
import { PROVIDERS, type Integration, type IntegrationProvider } from "./model";
import { ProvidersTable } from "./ProvidersTable";
import { StatusCell } from "./rows";
import { WebIntegrationHeader } from "./WebIntegrationHeader";
import { WORKSPACE_PROVIDERS, workspaceItems, type IntegrationWorkspaceMode } from "./workspaceModel";
import type { SessionUser } from "../../types";

vi.hoisted(() => {
  vi.stubGlobal("window", { location: { origin: "https://example.test" } });
});
afterAll(() => vi.unstubAllGlobals());

function integration(provider: IntegrationProvider, overrides: Partial<Integration> = {}): Integration {
  return {
    id: Object.keys(PROVIDERS).indexOf(provider) + 1, provider, kind: PROVIDERS[provider].kind, name: `Name ${provider}`,
    hasSecret: false, secretMasked: "", isActive: true, config: {} as Integration["config"],
    channel: null, status: "UNCHECKED", lastCheckedAt: null, lastError: "", createdAt: "", updatedAt: "",
    ...overrides,
  };
}
const rows = (Object.keys(PROVIDERS) as IntegrationProvider[]).map(provider => integration(provider));
const noop = () => undefined;
const handlers = { testingId: null, onTest: noop, onEdit: noop, onToggleActive: noop, onDelete: noop };

describe("independent connection workspaces", () => {
  it.each<[IntegrationWorkspaceMode, IntegrationProvider[]]>([
    ["providers", ["OPENROUTER", "CUSTOM", "DEMO", "YANDEX_SPEECHKIT"]],
    ["widgets", ["WEB"]],
    ["messengers", ["TELEGRAM", "MAX", "VK"]],
    ["mail", ["EMAIL"]],
    ["servers", ["MCP", "HTTP"]],
  ])("keeps %s limited to its intended connection types", (mode, expected) => {
    expect(workspaceItems(rows, mode).map(item => item.provider).sort()).toEqual([...expected].sort());
    const kind = mode === "providers" ? "LLM_PROVIDER" : mode === "servers" ? "EXTERNAL_SERVER" : "MESSENGER";
    expect(integrationProviderOptions(kind, WORKSPACE_PROVIDERS[mode]).map(([provider]) => provider).sort()).toEqual([...expected].sort());
  });

  it("keeps notification bots and disconnected channels available for management", () => {
    const notifier = integration("TELEGRAM", { isActive: false, status: "ERROR", config: { purpose: "notifications" } as Integration["config"] });
    expect(workspaceItems([notifier], "messengers")).toEqual([notifier]);
    expect(workspaceItems([notifier], "widgets")).toEqual([]);
  });

  it("filters MCP and HTTP without exposing channels or providers", () => {
    expect(workspaceItems(rows, "servers", "MCP").map(item => item.provider)).toEqual(["MCP"]);
    expect(workspaceItems(rows, "servers", "HTTP").map(item => item.provider)).toEqual(["HTTP"]);
  });

  it("does not offer unrelated providers even if the caller supplies them", () => {
    expect(integrationProviderOptions("MESSENGER", ["OPENROUTER", "MCP", "WEB"]).map(([provider]) => provider)).toEqual(["WEB"]);
    expect(integrationProviderOptions("MESSENGER", [])).toEqual([]);
  });

  it.each(["EMPLOYEE", "SUPERVISOR"] as const)("does not expose management forms to %s", role => {
    const html = renderToStaticMarkup(<IntegrationWorkspacePage mode="widgets" user={{ role } as SessionUser}
      openWebIntegration={noop} openServer={noop} createServer={noop} />);
    expect(html).toContain(t("settings.settings_available_owner_administrators"));
    expect(html).not.toContain(t("navigation.add_widget"));
  });
});

describe("contextual connection presentation", () => {
  it("uses channel routing and omits server-specific help on widget and messenger tables", () => {
    const html = renderToStaticMarkup(<ConnectionsTable items={[integration("WEB")]} context="channels" {...handlers} />);
    expect(html).toContain(t("navigation.routing"));
    expect(html).not.toContain(t("servers.agent_tools"));
    expect(html).not.toContain(t("servers.list_note"));
  });

  it("keeps server tools and their help in the tools table", () => {
    const item = integration("MCP", { externalServer: { type: "mcp", url: "https://example.test/mcp", description: "", headers: [], tools: [] } });
    const html = renderToStaticMarkup(<ConnectionsTable items={[item]} context="servers" {...handlers} />);
    expect(html).toContain(t("ai.tools"));
    expect(html).toContain(t("servers.list_note"));
  });

  it("keeps SpeechKit visible with its connection configuration", () => {
    const item = integration("YANDEX_SPEECHKIT", { config: { folderId: "folder-demo" } as Integration["config"] });
    const html = renderToStaticMarkup(<ProvidersTable items={[item]} {...handlers} />);
    expect(html).toContain("Yandex SpeechKit");
    expect(html).toContain(t("navigation.speech_folder", { folder: "folder-demo" }));
  });

  it("does not describe a disabled speech provider as a stopped messenger", () => {
    const html = renderToStaticMarkup(<StatusCell integration={integration("YANDEX_SPEECHKIT", { isActive: false })} />);
    expect(html).toContain(t("navigation.provider_disabled"));
    expect(html).not.toContain(t("settings.receiving_sending_messages_stopped"));
  });

  it("returns a widget to Widgets instead of the old Settings/Integrations hierarchy", () => {
    const html = renderToStaticMarkup(<WebIntegrationHeader integration={integration("WEB")} onBack={noop} />);
    expect(html).toContain(t("navigation.widgets"));
    expect(html).not.toContain(t("common.settings"));
    expect(html).not.toContain(t("common.integrations"));
  });
});
