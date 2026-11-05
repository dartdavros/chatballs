import { describe, expect, it } from "vitest";
import { appendDictation, DraftAttempt } from "./draft";

describe("dictation draft", () => {
  it("appends once to the latest edited draft and ignores cancelled or stale results", () => {
    const attempt = new DraftAttempt();
    let draft = "Initial";
    const first = attempt.begin();
    draft += " with edits";
    const append = (text: string) => { draft = appendDictation(draft, text); };
    expect(attempt.accept(first, " recognized", append)).toBe(true);
    expect(attempt.accept(first, "duplicate", append)).toBe(false);
    expect(draft).toBe("Initial with edits recognized");
    const cancelled = attempt.begin(); attempt.cancel();
    expect(attempt.accept(cancelled, "cancelled", append)).toBe(false);
    const stale = attempt.begin(); const current = attempt.begin();
    expect(attempt.accept(stale, "stale", append)).toBe(false);
    expect(attempt.accept(current, "new", append)).toBe(true);
    expect(draft).toBe("Initial with edits recognized new");
  });

  it("retains all text above the ordinary send limit", () => {
    const draft = appendDictation("x".repeat(4000), "recognized");
    expect(draft).toBe("x".repeat(4000) + " recognized");
    expect(appendDictation("line\n", "text")).toBe("line\ntext");
  });
});
