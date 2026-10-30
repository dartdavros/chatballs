import { t, tn, fmt } from "../../../i18n";
import { valueOptions } from "./bindingOptions";
import { sameReference } from "./referenceModel";
import type { Block, EditorCatalog, ScenarioDocument } from "./types";

export function stepIcon(step: Block) {
  return ({ action: "transfer", if: "swap", foreach: "list", parallel: "transfer", call: "link", wait: "clock", try: "warning" } as const)[step.kind];
}
export function stepSummary(step: Block, document: ScenarioDocument, catalog: EditorCatalog) {
  const count = (steps?: Block[]) => tn("scenarios.step_count", steps?.length ?? 0);
  if (step.kind === "action") return catalog.connections.find(c => String(c.id) === step.connection)?.name ?? t("scenarios.chatballs");
  if (step.kind === "if") return t("scenarios.if_summary", { yes: count(step.then), no: count(step.else) });
  if (step.kind === "try") return t("scenarios.try_summary", { body: count(step.body), catch: count(step.catch) });
  if (step.kind === "parallel") return t("scenarios.parallel_summary", { branches: tn("scenarios.branch_count", step.branches?.length ?? 0) });
  if (step.kind === "foreach") {
    const list = valueOptions(document, catalog, step.id).find(o => sameReference(o.binding, step.list));
    return t("scenarios.foreach_summary", { list: list?.label ?? t("scenarios.list_missing"), steps: count(step.body) });
  }
  if (step.kind === "call") {
    const target = catalog.scenarios.find(s => s.id === step.scenario);
    return t("scenarios.call_summary", { name: target?.name ?? t("scenarios.select"), filled: fmt.number(Object.keys(step.inputs ?? {}).length),
      total: fmt.number(Object.keys(target?.parameters.properties ?? {}).length) });
  }
  if (step.mode === "duration") {
    const seconds = step.duration ?? 0;
    const [divisor, key] = seconds && seconds % 86400 === 0 ? [86400, "scenarios.duration_days"] as const
      : seconds && seconds % 3600 === 0 ? [3600, "scenarios.duration_hours"] as const : [60, "scenarios.duration_minutes_count"] as const;
    return tn(key, seconds / divisor);
  }
  if (step.mode === "clock") return [t(`scenarios.day_${step.day ?? "next"}`), step.date, step.time, step.timezone].filter(Boolean).join(" · ");
  if (step.mode === "until") return t("scenarios.until_summary", { date: typeof step.until?.value === "string" && Number.isFinite(Date.parse(step.until.value)) ? fmt.shortDateTime(step.until.value) : t("scenarios.select") });
  return t("scenarios.wait_summary", { mode: t(`scenarios.wait_${step.mode ?? "reply"}`), hours: fmt.number((step.timeout ?? 86400) / 3600) });
}
