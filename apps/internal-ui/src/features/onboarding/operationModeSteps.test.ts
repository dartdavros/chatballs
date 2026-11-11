import { afterEach, expect, it, vi } from "vitest";

afterEach(() => vi.unstubAllGlobals());

async function steps(mode: string) {
  vi.stubGlobal("window", { location: { origin: "https://example.test" } });
  const { operationModeSteps } = await import("./operationModeSteps");
  return operationModeSteps(false, mode);
}

it("keeps the AI checklist when agents are enabled", async () => {
  const items = await steps("AI_AGENTS");
  expect(items).toHaveLength(7);
  expect(items.map((step) => step.key)).toContain("agentActive");
  expect(items.map((step) => step.key)).toContain("providerConnected");
});

it("opens the standalone sidebar destinations for providers, messengers and widgets", async () => {
  const items = await steps("AI_AGENTS");
  const destinations = [
    ["providerConnected", "aiProviders", "nav-ai-providers"],
    ["connectionBound", "messengers", "nav-messengers"],
    ["widgetPublished", "widgets", "nav-widgets"],
  ];
  for (const [key, route, element] of destinations) {
    const step = items.find((item) => item.key === key)!;
    expect(step.target).toMatchObject({ route, element });
    expect(step.target.section).toBeUndefined();
  }
});

it("prepares the operator journey without requiring AI configuration or an AI answer", async () => {
  const items = await steps("OPERATORS_ONLY");
  expect(items.map((step) => step.key)).toEqual(["connectionBound", "widgetPublished", "employeeInvited", "firstConversation"]);
  const last = items.at(-1)!;
  const { t } = await import("../../i18n");
  expect(last.preview.tone).toBe("waiting");
  expect(last.preview.rows.map((row) => row.label)).not.toContain(t("onboarding.s8.row2_label"));
  expect(last.instructions).toContain(t("onboarding.operator_check_reply"));
  expect(last.instructions).not.toContain(t("onboarding.s8.do_3"));
});
