import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";

import type { SessionUser } from "../../types";
import { RealtimeProvider } from "../realtime/RealtimeProvider";

afterEach(() => vi.unstubAllGlobals());

async function checklist(user: SessionUser) {
  vi.stubGlobal("window", { location: { origin: "https://example.test" } });
  const { useOnboardingState } = await import("./useOnboarding");
  let keys: string[] = [];
  function Harness() {
    const model = useOnboardingState({ user, setRoute: () => {}, openSettings: () => {} });
    keys = model.steps.map(step => step.key);
    return null;
  }
  renderToStaticMarkup(<RealtimeProvider><Harness /></RealtimeProvider>);
  return keys;
}

it.each(["OWNER", "ADMIN"] as const)("uses current platform authority for the %s checklist", async role => {
  const user = { role, isInstanceAdmin: false, canManagePlatform: true } as SessionUser;
  expect(await checklist(user)).toContain("platformConfigured");
  expect(await checklist({ ...user, canManagePlatform: false })).not.toContain("platformConfigured");
});

it("keeps the global administrator checklist for a legacy session", async () => {
  expect(await checklist({ role: "OWNER", isInstanceAdmin: true } as SessionUser)).toContain("platformConfigured");
});
