import { afterEach, describe, expect, it, vi } from "vitest";
import { scheduleScenarioValidation } from "./scenarioValidation";
import type { Issue } from "./types";

const required: Issue[] = [{ path: "steps.0.inputs.fields.owner", code: "required", message: "Required" }];

describe("draft validation scheduling", () => {
  afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); });

  it("replaces old errors with the checked draft and keeps errors on other fields", async () => {
    vi.useFakeTimers();
    let issues = required;
    const remaining = [{ ...required[0], path: "steps.0.inputs.fields.stage" }];
    const check = vi.fn(async () => ({ issues: remaining }));
    const cancel = scheduleScenarioValidation(check, next => { issues = next; }, vi.fn());
    await vi.advanceTimersByTimeAsync(299);
    expect(check).not.toHaveBeenCalled();
    expect(issues).toEqual(required);
    await vi.advanceTimersByTimeAsync(1);
    expect(issues).toEqual(remaining);
    cancel();
    scheduleScenarioValidation(async () => ({ issues: [] }), next => { issues = next; }, vi.fn());
    await vi.advanceTimersByTimeAsync(300);
    expect(issues).toEqual([]);
  });

  it("debounces edits and ignores an obsolete response even if the request cannot abort", async () => {
    vi.useFakeTimers();
    const skipped = vi.fn();
    const apply = vi.fn();
    const fail = vi.fn();
    const cancelSkipped = scheduleScenarioValidation(skipped, apply, fail);
    cancelSkipped();
    let finish!: (result: { issues: Issue[] }) => void;
    let signal!: AbortSignal;
    const cancel = scheduleScenarioValidation(current => {
      signal = current;
      return new Promise(resolve => { finish = resolve; });
    }, apply, fail);
    await vi.advanceTimersByTimeAsync(300);
    expect(skipped).not.toHaveBeenCalled();
    cancel();
    expect(signal.aborted).toBe(true);
    scheduleScenarioValidation(async () => ({ issues: [] }), apply, fail);
    await vi.advanceTimersByTimeAsync(300);
    finish({ issues: required });
    await vi.advanceTimersByTimeAsync(0);
    expect(apply.mock.calls).toEqual([[[]]]);
    expect(fail).not.toHaveBeenCalled();
  });

  it("reports a failed check without clearing errors and suppresses cancelled failures", async () => {
    vi.useFakeTimers();
    const apply = vi.fn();
    const fail = vi.fn();
    scheduleScenarioValidation(async () => { throw new Error("Unavailable"); }, apply, fail);
    await vi.advanceTimersByTimeAsync(300);
    expect(fail).toHaveBeenCalledOnce();
    expect(apply).not.toHaveBeenCalled();
    const cancel = scheduleScenarioValidation(async () => { cancel(); throw new Error("Aborted"); }, apply, fail);
    await vi.advanceTimersByTimeAsync(300);
    expect(fail).toHaveBeenCalledOnce();
  });
});
