import { fieldControl } from "../services/connect/fieldControls";
import type { ServiceField } from "../services/types";
import { childLists, operationFor } from "./model";
import type { Block, EditorCatalog, ScenarioDocument } from "./types";

export function unavailableField(field: ServiceField): boolean {
  if (field.control && !["lookup@1", "file@1"].includes(field.control)) return !fieldControl(field);
  if (["file", "lookup"].includes(field.type)) return false;
  if (field.type === "object") return (field.fields ?? []).some(unavailableField);
  if (field.type === "array") return !field.items || unavailableField(field.items);
  return !fieldControl(field);
}
export function unavailableScenarioControl(document: ScenarioDocument, catalog: EditorCatalog): boolean {
  function steps(items: Block[]): boolean {
    return items.some(step => {
      const schema = step.kind === "action" ? operationFor(catalog, step)?.input : undefined;
      return Boolean(schema && unavailableField(schema)) || childLists(step).some(([, list]) => steps(list));
    });
  }
  function bindings(value: unknown): boolean {
    if (!value || typeof value !== "object") return false;
    if (Array.isArray(value)) return value.some(bindings);
    const row = value as Record<string, unknown>;
    if (typeof row.source === "string") {
      const transform = catalog.transforms.find(t => t.key === row.transform);
      return Boolean(transform && unavailableField(transform.arguments));
    }
    return Object.values(row).some(bindings);
  }
  return steps(document.steps) || bindings(document);
}
