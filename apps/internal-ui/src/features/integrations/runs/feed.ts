import type { FeedRow } from "../../conversations/feed";
import type { RunSummary } from "./types";

export type RunFeedRow = { kind: "service_run"; key: string; createdAt: string; run: RunSummary };
export function mergeRunFeed(messages: FeedRow[], runs: RunSummary[], olderMessages: boolean, olderRuns: boolean): Array<FeedRow | RunFeedRow> {
  const time = (value: string) => new Date(value).getTime();
  const oldestRun = runs.reduce((oldest, run) => Math.min(oldest, time(run.createdAt)), Infinity);
  const floor = Math.max(olderMessages && messages.length ? time(messages[0].createdAt) : -Infinity,
    olderRuns && runs.length ? oldestRun : -Infinity);
  const rows: Array<FeedRow | RunFeedRow> = [...messages, ...runs.map(run => ({
    kind: "service_run" as const, key: `run:${run.id}`, createdAt: run.createdAt, run,
  }))];
  // Stable sort preserves the message/comment order already decided by the
  // conversation feed when timestamps are equal.
  return rows.filter(row => time(row.createdAt) >= floor).sort((a, b) => time(a.createdAt) - time(b.createdAt));
}
