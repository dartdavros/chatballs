import { t } from "../../i18n";
import type { ConversationListFilters } from "./model";

export type DialogScope =
  | { kind: "all" }
  | { kind: "group"; id: number; label: string }
  | { kind: "ungrouped" }
  | { kind: "agent"; id: number; label: string }
  | { kind: "assignee"; id: number; label: string };

export function scopeFilters(scope: DialogScope): ConversationListFilters {
  if (scope.kind === "group") return { group: String(scope.id) };
  if (scope.kind === "ungrouped") return { group: "none" };
  if (scope.kind === "agent") return { agent: scope.id };
  if (scope.kind === "assignee") return { assigned: scope.id };
  return {};
}

export function scopeLabel(scope: DialogScope): string {
  if (scope.kind === "group") return scope.label;
  if (scope.kind === "ungrouped") return t("common.no_group");
  if (scope.kind === "agent") return scope.label;
  if (scope.kind === "assignee") return scope.label;
  return t("profile.all_conversations");
}
