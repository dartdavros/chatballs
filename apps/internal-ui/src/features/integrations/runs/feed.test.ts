import { describe, expect, it } from "vitest";
import { conversationFeed } from "../../conversations/feed";
import { mergeRunFeed } from "./feed";
import type { RunSummary } from "./types";

const at = (minute: number) => `2026-10-30T12:${String(minute).padStart(2, "0")}:00Z`;
const run = (id: string, minute: number): RunSummary => ({ id, number: 1, name: "Run", connection: "Service", state: "completed",
  stateLabel: "Completed", initiator: "Employee", conversationId: 1, createdAt: at(minute), finishedAt: at(minute),
  cancelRequested: false, dataCleared: false, revision: 1, definitionUpdatedAt: null, progress: [] });
const messages = conversationFeed({ hasOlder: false, items: [
  { id: 1, author: "CONTACT", text: "Hello", createdAt: at(10) },
  { id: 2, author: "CONTACT", text: "Again", createdAt: at(30) },
] }, { hasOlder: false, items: [{ id: 1, conversationId: 1, audience: "INTERNAL", text: "Note", author: { id: 1, name: "Employee" }, createdAt: at(10), operationId: "note-1" }] });

describe("runs in the conversation timeline", () => {
  it("merges by time while preserving the conversation's equal-time order", () => {
    expect(mergeRunFeed(messages, [run("one", 20)], false, false).map(row => row.key)).toEqual(["m1", "c1", "run:one", "m2"]);
  });
  it("keeps the incomplete run window's boundary until older runs load", () => {
    expect(mergeRunFeed(messages, [run("one", 20)], false, true).map(row => row.key)).toEqual(["run:one", "m2"]);
    expect(mergeRunFeed(messages, [run("one", 20)], false, false)).toHaveLength(4);
  });
  it("does not put old runs beyond the incomplete message window", () => {
    expect(mergeRunFeed(messages, [run("old", 5), run("one", 20)], true, false).map(row => row.key)).toEqual(["m1", "c1", "run:one", "m2"]);
  });
});
