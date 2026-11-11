import { describe, expect, it } from "vitest";
import type { IntegrationKind, IntegrationProvider } from "../features/integrations/model";
import { integrationDestination } from "./LegacyIntegrationRoute";

describe("legacy integration destinations", () => {
  it.each<[IntegrationKind, IntegrationProvider, string, number | null]>([
    ["MESSENGER", "WEB", "webIntegrationSettings", 42],
    ["EXTERNAL_SERVER", "MCP", "externalServerSettings", 42],
    ["EXTERNAL_SERVER", "HTTP", "externalServerSettings", 42],
    ["MESSENGER", "TELEGRAM", "messengers", null],
    ["MESSENGER", "MAX", "messengers", null],
    ["MESSENGER", "VK", "messengers", null],
    ["MESSENGER", "EMAIL", "emailIntegrations", null],
    ["LLM_PROVIDER", "CUSTOM", "aiProviders", null],
    ["SPEECH_PROVIDER", "YANDEX_SPEECHKIT", "aiProviders", null],
  ])("opens the correct destination for %s / %s", (kind, provider, route, id) => {
    expect(integrationDestination({ id: 42, kind, provider })).toEqual({ route, id });
  });
});
