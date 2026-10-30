import { t } from "../../../i18n";
import type { Block, BlockKind, BlockLocation, DataSchema, EditorCatalog, Operation, ScenarioDocument } from "./types";
import type { ServiceField } from "../services/types";

export const id = () => crypto.randomUUID();
export const blankConditions = () => ({ mode: "all" as const, items: [] });
export function emptyDocument(): ScenarioDocument {
  return { version: 1, parameters: { type: "object", properties: {} }, results: { type: "object", properties: {} }, outputs: {},
    triggers: [{ id: id(), kind: "staff" }], conditions: blankConditions(), steps: [], synchronization: [],
    access: { staff: [], groups: [], aiMode: "confirm", delegated: false, scope: "conversation", confirm: "effects" } };
}
export function newBlock(kind: BlockKind): Block {
  const block: Block = { id: id(), kind };
  if (kind === "action") Object.assign(block, { connection: "", target: "", inputs: {}, onError: "stop" });
  if (kind === "if") Object.assign(block, { condition: blankConditions(), then: [], else: [] });
  if (kind === "foreach") Object.assign(block, { body: [], list: { source: "step", step: "", path: "" }, concurrency: 1, onError: "continue" });
  if (kind === "parallel") Object.assign(block, { branches: [[], []], onError: "wait" });
  if (kind === "try") Object.assign(block, { body: [], catch: [], after: "continue" });
  if (kind === "call") Object.assign(block, { scenario: "", inputs: {} });
  if (kind === "wait") Object.assign(block, { mode: "reply", timeout: 86400, onTimeout: "continue" });
  return block;
}
export function childLists(block: Block): Array<[string, Block[]]> {
  if (block.kind === "if") return [["then", block.then ?? []], ["else", block.else ?? []]];
  if (block.kind === "foreach") return [["body", block.body ?? []]];
  if (block.kind === "try") return [["body", block.body ?? []], ["catch", block.catch ?? []]];
  if (block.kind === "parallel") return (block.branches ?? []).map((branch, i) => [`branches.${i}`, branch]);
  return [];
}
export function findBlock(steps: Block[], target: string): Block | undefined {
  for (const step of steps) {
    if (step.id === target) return step;
    for (const [, list] of childLists(step)) { const result = findBlock(list, target); if (result) return result; }
  }
}
export function listAt(steps: Block[], location: BlockLocation): Block[] {
  if (!location.parent) return steps;
  const parent = findBlock(steps, location.parent);
  return parent ? childLists(parent).find(([key]) => key === location.branch)?.[1] ?? [] : [];
}
export function blockPath(steps: Block[], target: string, path = "steps"): string {
  for (const [index, step] of steps.entries()) {
    const at = `${path}.${index}`;
    if (step.id === target) return at;
    for (const [key, list] of childLists(step)) { const found = blockPath(list, target, `${at}.${key}`); if (found) return found; }
  }
  return "";
}
export function removeBlock(steps: Block[], target: string): boolean {
  const index = steps.findIndex(step => step.id === target);
  if (index >= 0) { steps.splice(index, 1); return true; }
  return steps.some(step => childLists(step).some(([, list]) => removeBlock(list, target)));
}
export function copyBlock(block: Block): Block {
  const copied = structuredClone(block);
  const ids = new Map<string, string>();
  const walk = (step: Block) => { ids.set(step.id, id()); childLists(step).forEach(([, list]) => list.forEach(walk)); };
  walk(copied);
  const replace = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(replace);
    if (value && typeof value === "object") {
      if ("source" in value && typeof value.source === "string") {
        const binding = { ...value };
        if (typeof binding.source === "string" && ["step", "item", "error"].includes(binding.source) && "step" in binding && typeof binding.step === "string") binding.step = ids.get(binding.step) ?? binding.step;
        return binding;
      }
      return Object.fromEntries(Object.entries(value).map(([key, child]) =>
        [key, key === "id" && typeof child === "string" ? ids.get(child) ?? child : replace(child)]));
    }
    return value;
  };
  return replace(copied) as Block;
}
export function operations(catalog: EditorCatalog, connection: string): Operation[] {
  if (connection === "chatballs") return catalog.nativeActions;
  const adapter = catalog.adapters.find(a => a.key === catalog.connections.find(c => String(c.id) === connection)?.adapter);
  return (adapter?.operations ?? []).map(operation => ({ ...operation, key: `service:${operation.key}` }));
}
export function operationFor(catalog: EditorCatalog, block: Block) {
  return operations(catalog, block.connection ?? "").find(operation => operation.key === block.target);
}
export function blockTitle(block: Block, catalog: EditorCatalog) {
  return block.name || (block.kind === "action" ? operationFor(catalog, block)?.title : null) || t(`scenarios.block_${block.kind}`);
}
export function schemaField(name: string, schema: DataSchema): ServiceField {
  return { name, type: schema.type, title: schema.title || name, required: schema.required ?? false, nullable: schema.nullable ?? false,
    hint: "", placeholder: "", secret: false, control: "", lookup: schema.lookup, open: schema.open,
    fields: Object.entries(schema.properties ?? {}).map(([key, child]) => schemaField(key, child)),
    items: schema.items ? schemaField("", schema.items) : undefined,
    options: schema.options?.map(value => ({ value, label: String(value) })) };
}
