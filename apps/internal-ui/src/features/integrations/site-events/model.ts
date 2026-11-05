import type { SiteEventField, SiteEventRule } from "@chatballs/contracts";

export type DraftField = { name: string; type: SiteEventField["type"]; required: boolean;
  maxLength: string; minimum: string; maximum: string };
export type DraftRule = Omit<SiteEventRule, "schema"> & { schema: DraftField[] };
export const emptyField = (): DraftField => ({ name: "", type: "string", required: false, maxLength: "120", minimum: "0", maximum: "100" });

export function draftOf(rule?: SiteEventRule | null): DraftRule {
  return { name: rule?.name ?? "", invitation: rule?.invitation ?? "", scenario: rule?.scenario ?? "", active: rule?.active ?? false,
    id: rule?.id, schema: (rule?.schema ?? []).map((field) => ({ ...emptyField(), ...field,
      maxLength: field.type === "string" ? String(field.maxLength) : "120",
      minimum: field.type === "number" ? String(field.minimum) : "0",
      maximum: field.type === "number" ? String(field.maximum) : "100" })) };
}

export function validatedRule(draft: DraftRule): SiteEventRule | null {
  if (!/^[a-zA-Z][a-zA-Z0-9_.-]{0,79}$/.test(draft.name) || !draft.invitation.trim()
    || draft.invitation.trim().length > 1000 || !draft.scenario || draft.schema.length > 30) return null;
  const schema: SiteEventField[] = [], seen = new Set<string>();
  for (const field of draft.schema) {
    if (!/^[a-z][a-z0-9_]{0,39}$/.test(field.name) || seen.has(field.name)) return null;
    seen.add(field.name);
    const common = { name: field.name, required: field.required };
    if (field.type === "boolean") schema.push({ ...common, type: "boolean" });
    else if (field.type === "string") {
      const maxLength = Number(field.maxLength);
      if (!Number.isInteger(maxLength) || maxLength < 1 || maxLength > 4000) return null;
      schema.push({ ...common, type: "string", maxLength });
    } else {
      const minimum = Number(field.minimum), maximum = Number(field.maximum);
      if (!field.minimum.trim() || !field.maximum.trim() || !Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum > maximum) return null;
      schema.push({ ...common, type: "number", minimum, maximum });
    }
  }
  return { ...draft, invitation: draft.invitation.trim(), schema };
}
