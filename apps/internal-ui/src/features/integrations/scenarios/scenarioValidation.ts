import type { Issue } from "./types";

// A check only reads the draft. Cancelling also guards against a response
// arriving after another edit, a save, navigation, or unmount.
export function scheduleScenarioValidation(
  check: (signal: AbortSignal) => Promise<{ issues: Issue[] }>,
  apply: (issues: Issue[]) => void,
  fail: () => void,
) {
  const controller = new AbortController();
  const timer = setTimeout(async () => {
    try {
      const result = await check(controller.signal);
      if (!controller.signal.aborted) apply(result.issues);
    } catch {
      if (!controller.signal.aborted) fail();
    }
  }, 300);
  return () => { clearTimeout(timer); controller.abort(); };
}
