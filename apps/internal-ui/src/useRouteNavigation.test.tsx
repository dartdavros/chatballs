import { useState } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { routeFromPath } from "./router";
import { useRouteNavigation } from "./useRouteNavigation";
import { registerNavigationGuard, releaseNavigationGuard } from "./shared/navigationGuard";

const organization = "12345678-1234-1234-1234-123456789abc";
const prefix = `/organizations/${organization}`;
type Navigation = ReturnType<typeof useRouteNavigation>;

function browser(path: string) {
  let location = new URL(path, "https://example.test");
  const history = {
    state: null as unknown,
    pushState: vi.fn((state: unknown, _title: string, next: string) => {
      history.state = state;
      location = new URL(next, location);
    }),
    replaceState: vi.fn((state: unknown, _title: string, next: string) => {
      history.state = state;
      location = new URL(next, location);
    }),
  };
  vi.stubGlobal("window", { get location() { return location; }, history });
  return history;
}

// Как и в useEmailComposerDraft.test.tsx, React повторяет render после действий;
// это проверяет состояние хука без DOM, API или дополнительных зависимостей.
function navigate(actions: Array<(model: Navigation) => void>) {
  const initial = routeFromPath(window.location.pathname, window.location.search);
  const snapshots: Array<{ route: string; version: number; integrationId: number | null; url: string }> = [];
  function Harness() {
    const [phase, setPhase] = useState(0);
    const model = useRouteNavigation(initial, organization);
    snapshots.push({ route: model.route, version: model.navigationVersion,
      integrationId: model.selectedIntegrationId, url: `${window.location.pathname}${window.location.search}` });
    if (phase < actions.length) {
      actions[phase](model);
      setPhase(phase + 1);
    }
    return null;
  }
  renderToStaticMarkup(<Harness />);
  return snapshots;
}

afterEach(() => {
  releaseNavigationGuard();
  vi.unstubAllGlobals();
});

describe("route navigation state", () => {
  it("refreshes the scenario workspace when its active menu item clears the selected scenario", () => {
    const history = browser(`${prefix}/scenarios?scenario=selected`);
    const states = navigate([model => model.navigate("scenarios")]);
    expect(states.map(state => [state.route, state.version])).toEqual([["scenarios", 0], ["scenarios", 1]]);
    expect(states[1].url).toBe(`${prefix}/scenarios`);
    expect(history.pushState).toHaveBeenCalledOnce();
  });

  it("refreshes the same route when a history entry changes scenario query", () => {
    browser(`${prefix}/scenarios?scenario=selected`);
    const states = navigate([model => {
      window.history.replaceState({}, "", `${prefix}/scenarios?runs=1&run=previous`);
      model.applyRouteState(routeFromPath(window.location.pathname, window.location.search));
    }]);
    expect(states[1]).toMatchObject({ route: "scenarios", version: 1, url: `${prefix}/scenarios?runs=1&run=previous` });
  });

  it("keeps the editor and version unchanged until leaving is approved", () => {
    const history = browser(`${prefix}/scenarios?scenario=unsaved`);
    let proceed: (() => void) | undefined;
    registerNavigationGuard(next => { proceed = next; });
    const states = navigate([
      model => model.navigate("chat"),
      () => { expect(history.pushState).not.toHaveBeenCalled(); proceed?.(); },
    ]);
    expect(states.map(state => [state.route, state.version])).toEqual([["scenarios", 0], ["scenarios", 0], ["chat", 1]]);
    expect(states[1].url).toBe(`${prefix}/scenarios?scenario=unsaved`);
    expect(states[2].url).toBe(`${prefix}/chat`);
  });

  it("returns to the skills library from its active menu item after the editor guard allows leaving", () => {
    const history = browser(`${prefix}/agents/skills?skill=unsaved`);
    let proceed: (() => void) | undefined;
    registerNavigationGuard(next => { proceed = next; });
    const states = navigate([
      model => model.navigate("skills"),
      () => { expect(history.pushState).not.toHaveBeenCalled(); proceed?.(); },
    ]);
    expect(states.map(state => [state.route, state.version])).toEqual([["skills", 0], ["skills", 0], ["skills", 1]]);
    expect(states[1].url).toBe(`${prefix}/agents/skills?skill=unsaved`);
    expect(states[2].url).toBe(`${prefix}/agents/skills`);
  });

  it("refreshes skills when history restores another selected skill", () => {
    browser(`${prefix}/agents/skills?skill=first`);
    const states = navigate([model => {
      window.history.replaceState({}, "", `${prefix}/agents/skills?skill=second`);
      model.applyRouteState(routeFromPath(window.location.pathname, window.location.search));
    }]);
    expect(states[1]).toMatchObject({ route: "skills", version: 1, url: `${prefix}/agents/skills?skill=second` });
  });

  it("replaces a resolved legacy connection with its id and query intact", () => {
    const history = browser(`${prefix}/settings/integrations/31?section=tools`);
    const states = navigate([model => model.navigate("externalServerSettings", 31, true, organization, "?section=tools")]);
    expect(states[1]).toMatchObject({ route: "externalServerSettings", integrationId: 31, version: 1,
      url: `${prefix}/tools/31?section=tools` });
    expect(history.replaceState).toHaveBeenCalledOnce();
    expect(history.pushState).not.toHaveBeenCalled();
  });
});
