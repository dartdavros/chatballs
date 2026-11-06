import type { ScenarioDocument } from "./types";

/** Remove only editor-generated inputs after their last reference is removed. */
export function pruneInputs(document: ScenarioDocument) {
  const used = new Set<string>();
  const visit = (value: unknown) => {
    if (!value || typeof value !== "object") return;
    if (Array.isArray(value)) { value.forEach(visit); return; }
    const row = value as Record<string, unknown>;
    if (row.source === "constant") return;
    if (["input", "parameter"].includes(String(row.source)) && typeof row.name === "string") used.add(row.name);
    Object.values(row).forEach(visit);
  };
  visit(document.steps); visit(document.conditions); visit(document.outputs);
  for (const name of Object.keys(document.parameters.properties ?? {})) {
    if (/^input_[0-9a-f-]{36}$/i.test(name) && !used.has(name)) delete document.parameters.properties![name];
  }
}
