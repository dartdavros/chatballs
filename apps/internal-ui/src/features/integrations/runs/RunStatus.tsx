import { StatusPill } from "../../../shared/ui";
import type { RunState } from "./types";

export function RunStatus({ state, label }: { state: RunState; label: string }) {
  return <StatusPill status={state === "completed" ? "healthy" : state === "failed" ? "error"
    : state === "cancelled" ? "draft" : "pending"} label={label} />;
}
