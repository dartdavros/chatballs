import { t } from "../../../i18n";
import type { ServiceField } from "../services/types";
import { childLists, schemaField, blockTitle } from "./model";
import { aggregateOutput } from "./aggregateOutput";
import type { Binding, Block, EditorCatalog, ScenarioDocument } from "./types";

export type ValueOption = { key: string; label: string; binding: Binding; field: ServiceField };
type Scope = { steps: Block[]; items: Array<{ step: Block; field: ServiceField }>; errors: string[] };

function scopeAt(steps: Block[], target: string, initial: Scope, catalog: EditorCatalog, document: ScenarioDocument): Scope | null {
  const scope: Scope = { steps: [...initial.steps], items: [...initial.items], errors: [...initial.errors] };
  for (const step of steps) {
    if (step.id === target) return scope;
    for (const [key, list] of childLists(step)) {
      const nested = { steps: [...scope.steps], items: [...scope.items], errors: [...scope.errors] };
      if (step.kind === "foreach" && step.list) {
        const field = referenceField(step.list, scope, catalog, document);
        if (field?.items) nested.items.push({ step, field: field.items });
      }
      if (step.kind === "try" && key === "catch") nested.errors.push(step.id);
      const found = scopeAt(list, target, nested, catalog, document); if (found) return found;
    }
    scope.steps.push(step);
  }
  return null;
}
function eventField(document: ScenarioDocument, catalog: EditorCatalog) {
  const events = document.triggers.map(trigger => {
    const adapter = catalog.adapters.find(a => a.key === catalog.connections.find(c => String(c.id) === trigger.connection)?.adapter);
    return (trigger.kind === "chatballs" ? catalog.events : adapter?.events)?.find(event => event.key === trigger.event)?.payload;
  });
  return events.length && events.every(event => event && JSON.stringify(event) === JSON.stringify(events[0])) ? events[0] : undefined;
}
function referenceField(binding: Binding, scope: Scope, catalog: EditorCatalog, document: ScenarioDocument) {
  let root: ServiceField | undefined;
  if (binding.source === "step") { const step = scope.steps.find(s => s.id === binding.step); root = step && outputField(step, catalog); }
  if (binding.source === "item") root = scope.items.find(i => i.step.id === binding.step)?.field;
  if (binding.source === "context") root = catalog.context;
  if (binding.source === "event") root = eventField(document, catalog);
  if (binding.source === "parameter" || binding.source === "input") { const schema = document.parameters.properties?.[binding.name ?? ""]; root = schema && schemaField(binding.name!, schema); }
  return root && fieldAt(root, binding.path ?? "");
}
export function outputField(step: Block, catalog: EditorCatalog) {
  return aggregateOutput(step, catalog);
}
export function fieldAt(field: ServiceField, path: string): ServiceField | undefined {
  let result: ServiceField | undefined = field;
  for (const part of path.split(".").filter(Boolean)) result = result?.fields?.find(f => f.name === part);
  return result;
}
function fields(field: ServiceField, path = "", label = ""): Array<{ path: string; label: string; field: ServiceField }> {
  const own = [{ path, label: label || field.title, field }];
  return [...own, ...(field.fields ?? []).flatMap(child => fields(child, path ? `${path}.${child.name}` : child.name, label ? `${label} · ${child.title}` : child.title))];
}
export function valueOptions(document: ScenarioDocument, catalog: EditorCatalog, current: string): ValueOption[] {
  const scope = scopeAt(document.steps, current, { steps: [], items: [], errors: [] }, catalog, document) ?? { steps: [], items: [], errors: [] };
  const options: ValueOption[] = [];
  const add = (field: ServiceField, base: Binding, label: string) => {
    for (const child of fields(field)) {
      const binding = { ...base, path: child.path };
      options.push({ key: JSON.stringify(binding), label: [label, child.label].filter(Boolean).join(" · "), binding, field: child.field });
    }
  };
  add(catalog.context, { source: "context" }, t("scenarios.source_context"));
  Object.entries(document.parameters.properties ?? {}).forEach(([name, schema]) => {
    add(schemaField(name, schema), { source: "parameter", name }, t("scenarios.source_parameter"));
  });
  const event = eventField(document, catalog);
  if (event) add(event, { source: "event" }, t("scenarios.source_event"));
  scope.steps.forEach(step => {
    const field = outputField(step, catalog); if (field) add(field, { source: "step", step: step.id }, blockTitle(step, catalog));
    const binding: Binding = { source: "step", step: step.id, aspect: "state" };
    options.push({ key: JSON.stringify(binding), binding, label: `${blockTitle(step, catalog)} · ${t("scenarios.step_state")}`,
      field: { ...schemaField("state", { type: "enum", title: t("scenarios.step_state"), required: true }),
        options: [{ value: "completed", label: t("scenarios.step_completed") }, { value: "failed", label: t("scenarios.step_failed") }] } });
  });
  scope.items.forEach(item => add(item.field, { source: "item", step: item.step.id }, t("scenarios.source_item")));
  scope.errors.forEach(step => {
    const field = schemaField("", { type: "object", properties: { reason: { type: "string", title: t("common.error") },
      step: { type: "string", title: t("scenarios.steps") }, number: { type: "integer", title: t("scenarios.step_number", { number: "" }) },
      service: { type: "string", title: t("scenarios.service") }, run: { type: "string", title: t("scenarios.launch") } } });
    add(field, { source: "error", step }, t("scenarios.source_error"));
  });
  return options;
}
export function compatibleField(source: ServiceField, target: ServiceField): boolean {
  if (target.type === "json") return !source.nullable || target.nullable;
  if (source.type !== target.type && !(source.type === "integer" && target.type === "number")) return false;
  if (source.nullable && !target.nullable) return false;
  if (target.type === "lookup") return source.lookup === target.lookup;
  if (target.type === "enum") return (source.options ?? []).every(s => target.options?.some(t => typeof s.value === typeof t.value && s.value === t.value));
  if (target.type === "array") return Boolean(source.items && target.items && compatibleField(source.items, target.items));
  if (target.type === "object") return (target.fields ?? []).every(child => {
    const from = source.fields?.find(f => f.name === child.name);
    return from ? (!child.required || from.required) && compatibleField(from, child) : !child.required;
  });
  return true;
}
