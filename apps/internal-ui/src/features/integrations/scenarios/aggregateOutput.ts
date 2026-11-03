import { fmt, t } from "../../../i18n";
import type { ServiceField } from "../services/types";
import { blockTitle, operationFor, schemaField } from "./model";
import type { Block, EditorCatalog } from "./types";

const field = (name: string, type: "object" | "array" | "integer" | "string", title: string) => schemaField(name, { type, title });

export function aggregateOutput(block: Block, catalog: EditorCatalog, depth = 0): ServiceField | undefined {
  if (depth > 16) return undefined;
  if (block.kind === "action") return operationFor(catalog, block)?.output;
  if (block.kind === "call") {
    const called = catalog.scenarios.find(s => s.id === block.scenario);
    return called ? schemaField("", called.results) : undefined;
  }
  const entry = (steps: Block[]): ServiceField => {
    const outputs = field("steps", "object", t("scenarios.steps"));
    outputs.fields = steps.flatMap(step => {
      const output = aggregateOutput(step, catalog, depth + 1);
      return output ? [{ ...output, name: step.id, title: blockTitle(step, catalog), required: false }] : [];
    });
    const state = { ...field("state", "string", t("scenarios.step_state")), type: "enum",
      options: (["completed", "failed", "cancelled"] as const).map(value => ({ value, label: t(`runs.state_${value}`) })) };
    const error = field("error", "object", t("scenarios.source_error"));
    error.nullable = true;
    error.fields = ["reason", "step", "service", "run"].map(name => field(name, "string",
      t(name === "reason" ? "common.error" : name === "step" ? "scenarios.steps" : name === "service" ? "scenarios.service" : "scenarios.launch")));
    error.fields.push(field("number", "integer", t("runs.item_index")));
    const result = field("", "object", "");
    result.fields = [field("index", "integer", t("runs.item_index")), state, outputs, error];
    return result;
  };
  if (block.kind === "foreach") {
    const items = field("items", "array", t("runs.iteration_results")); items.items = entry(block.body ?? []);
    const errors = field("errors", "array", t("runs.iteration_errors")); errors.items = items.items;
    const result = field("", "object", ""); result.fields = [items, errors]; return result;
  }
  if (block.kind === "parallel") {
    const branches = field("branches", "object", t("runs.parallel_results"));
    branches.fields = (block.branches ?? []).map((steps, index) => ({ ...entry(steps), name: String(index),
      title: t("scenarios.branch", { number: fmt.number(index + 1) }) }));
    const result = field("", "object", ""); result.fields = [branches]; return result;
  }
  if (block.kind === "wait" && block.mode === "event") {
    const connection = catalog.connections.find(c => String(c.id) === block.connection);
    const events = block.connection ? catalog.adapters.find(a => a.key === connection?.adapter)?.events : catalog.events;
    const payload = events?.find(e => e.key === block.event)?.payload;
    if (payload) { const result = field("", "object", ""); result.fields = [{ ...payload, name: "event", title: t("scenarios.source_event"), required: false }]; return result; }
  }
  return undefined;
}
