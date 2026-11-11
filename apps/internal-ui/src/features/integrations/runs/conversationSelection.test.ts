import { describe, expect, it } from "vitest";
import { createConversationSelection } from "./conversationSelection";

describe("conversation action selection lifetime", () => {
  it("rejects a late completion after switching away and back to the same conversation", () => {
    const gate = createConversationSelection(1);
    const firstVisit = gate.enter(1);
    const running = gate.begin(firstVisit)!;
    gate.enter(2);
    gate.enter(1);
    expect(gate.isCurrent(running)).toBe(false);
    expect(gate.begin(firstVisit)).toBeNull();
    expect(gate.isContext(firstVisit)).toBe(false);
  });

  it("does not reopen a closed form or replace a subsequently selected action", () => {
    const gate = createConversationSelection(1);
    const context = gate.enter(1);
    const first = gate.begin(context)!;
    gate.close(context);
    expect(gate.isCurrent(first)).toBe(false);
    const second = gate.begin(context)!;
    expect(gate.isCurrent(first)).toBe(false);
    expect(gate.isCurrent(second)).toBe(true);
  });

  it("an old close cannot invalidate the current conversation selection", () => {
    const gate = createConversationSelection(1);
    const old = gate.enter(1);
    const current = gate.begin(gate.enter(2))!;
    gate.close(old);
    expect(gate.isCurrent(current)).toBe(true);
  });

  it("preserves a selection through ordinary rerenders and refuses a missing context", () => {
    const gate = createConversationSelection(null);
    expect(gate.begin(gate.enter(null))).toBeNull();
    const selected = gate.begin(gate.enter(9))!;
    gate.enter(9);
    expect(gate.isCurrent(selected)).toBe(true);
  });
});
