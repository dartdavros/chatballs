import { t } from "../../../i18n";
import { valueOptions, type ValueOption } from "./bindingOptions";
import type { Binding, Condition, EditorCatalog, ScenarioDocument } from "./types";
import { sameReference } from "./referenceModel";
export { sameReference } from "./referenceModel";

export function conditionKind(condition: Condition): string {
  if (condition.kind === "context_present") return "contact";
  if (condition.kind === "no_link" || condition.kind === "has_link") return "linked";
  if (condition.kind) return condition.kind;
  return condition.left?.source === "context" || !condition.left ? "field" : condition.left.source;
}
export function conditionOptions(document: ScenarioDocument, catalog: EditorCatalog, current: string): ValueOption[] {
  return valueOptions(document, catalog, current).filter(o => !["object", "array", "file"].includes(o.field.type));
}
export function newCondition(kind: string, options: ValueOption[]): Condition {
  if (kind === "contact") return { kind: "context_present", path: "contact", present: true };
  if (kind === "tag") return { kind: "tag", scope: "conversation", present: true };
  if (kind === "channel") return { kind: "channel", present: true };
  if (kind === "linked") return { kind: "no_link", connection: "", entity: "" };
  const left = options.find(o => o.binding.source === (kind === "field" ? "context" : kind))?.binding;
  return { left, op: left?.aspect ? "eq" : "filled", ...(left?.aspect ? { right: { source: "constant", value: "completed" } as Binding } : {}) };
}
export function conditionSummary(condition: Condition, document: ScenarioDocument, catalog: EditorCatalog, current = "") {
  if (condition.kind === "context_present") return t(condition.present === false ? "scenarios.contact_absent" : "scenarios.contact_present");
  if (condition.kind === "tag") return [catalog.labels.find(t => t.id === condition.tag)?.name, t(condition.present !== false ? "scenarios.tag_present" : "scenarios.tag_absent")].filter(Boolean).join(" · ");
  if (condition.kind === "channel") return [t("scenarios.channel"), t(condition.present === false ? "scenarios.op_ne" : "scenarios.op_eq"), catalog.channels.find(c => c.id === condition.connection)?.name].filter(Boolean).join(" · ");
  if (condition.kind === "no_link" || condition.kind === "has_link") return [catalog.connections.find(c => String(c.id) === String(condition.connection))?.name,
    t(condition.kind === "no_link" ? "scenarios.link_absent" : "scenarios.link_present")].filter(Boolean).join(" · ");
  const option = conditionOptions(document, catalog, current).find(o => sameReference(o.binding, condition.left));
  const op = condition.op as "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "contains" | "empty" | "filled";
  const right = option?.field.options?.find(o => o.value === condition.right?.value)?.label ?? condition.right?.value;
  return [option?.label, op && t(`scenarios.op_${op}`), right === undefined ? "" : String(right)].filter(Boolean).join(" · ") || t("scenarios.conditions");
}
